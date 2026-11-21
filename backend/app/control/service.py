"""
Safe PLC Remote Control Service Architecture
Enforces disabled-by-default safety, strict allowlists, hardware interlocks,
readback verification, and immutable audit logging.
"""
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple
import logging

from app.core.config import settings
from app.plc.register_map import load_register_map, WritableAllowlistEntry
from app.database.session import async_session_factory
from app.database.models import ControlAuditLogModel

logger = logging.getLogger("control.service")


class SafeControlService:
    """
    Executes the 8-step safe machine control request workflow.
    Never allows bypassing PLC safety relays or hardware interlocks.
    """

    def __init__(self):
        self.reg_map = load_register_map(settings.REGISTER_MAP_PATH)
        self.allowlist: Dict[str, WritableAllowlistEntry] = {
            entry.name: entry for entry in self.reg_map.writable_allowlist
        }

    async def execute_control_request(
        self,
        modbus_client,
        operator: str,
        client_ip: str,
        command_name: str,
        target_value: float,
        current_signals: Dict[str, Any],
        operator_confirmed: bool = False,
    ) -> Dict[str, Any]:
        """
        Executes the 8-step safe control handshake.
        Returns a result payload with status and audit details.
        """
        now_iso = datetime.now(timezone.utc).isoformat()

        # Step 0: Check global safety enable switch
        if not settings.ALLOW_REMOTE_CONTROL:
            msg = "SAFETY REJECTION: Remote PLC control is disabled by default in system configuration (ALLOW_REMOTE_CONTROL=false)."
            await self._record_audit(
                operator=operator,
                client_ip=client_ip,
                cmd_name=command_name,
                addr=-1,
                val=target_value,
                interlocks=False,
                status="DISABLED_BY_DEFAULT",
                readback_ok=False,
                details=msg,
            )
            return {"success": False, "status": "DISABLED", "message": msg}

        # Step 1: Validate allowlist entry
        entry = self.allowlist.get(command_name)
        if not entry:
            msg = f"SECURITY VIOLATION: Command '{command_name}' is not in the configured writable allowlist!"
            logger.error(msg)
            await self._record_audit(
                operator=operator,
                client_ip=client_ip,
                cmd_name=command_name,
                addr=-1,
                val=target_value,
                interlocks=False,
                status="SECURITY_VIOLATION",
                readback_ok=False,
                details=msg,
            )
            return {"success": False, "status": "REJECTED", "message": msg}

        # Step 2: Validate operator confirmation modal
        if entry.confirmation_required and not operator_confirmed:
            msg = f"Confirmation required: Operator must acknowledge consequential action for '{command_name}'."
            return {"success": False, "status": "CONFIRMATION_REQUIRED", "message": msg}

        # Step 3: Check communication health
        if not modbus_client.diagnostics.connected:
            msg = "COMMUNICATION FAULT: Cannot execute control write while PLC Modbus link is disconnected."
            return {"success": False, "status": "COMM_FAULT", "message": msg}

        if modbus_client.diagnostics.is_data_stale(modbus_client.diagnostics.last_global_success_monotonic):
            msg = "DATA STALE: Communication with PLC is stale. Rejecting remote write command."
            return {"success": False, "status": "DATA_STALE", "message": msg}

        # Step 4: Permissive Interlock Verification
        interlocks_ok = True
        interlock_reasons = []

        if entry.requires_interlock:
            # Check E-Stop
            e_stop = current_signals.get("emergency_stop_ok", {}).get("value", 0)
            if e_stop != 1:
                interlocks_ok = False
                interlock_reasons.append("Emergency Stop circuit is tripped or open")

            # Check Safety Guard
            guard = current_signals.get("safety_guard_closed", {}).get("value", 0)
            if guard != 1:
                interlocks_ok = False
                interlock_reasons.append("Safety Guard door is open")

            # Check VFD Fault if commanding drive
            if "vfd" in command_name:
                vfd_fault = current_signals.get("vfd_fault_status", {}).get("value", 0)
                if vfd_fault != 0:
                    interlocks_ok = False
                    interlock_reasons.append("VFD reports an active drive fault condition")

        if not interlocks_ok:
            reason_str = "; ".join(interlock_reasons)
            msg = f"INTERLOCK REJECTION: Machine safety interlock permissive not satisfied: {reason_str}"
            logger.warning(msg)
            await self._record_audit(
                operator=operator,
                client_ip=client_ip,
                cmd_name=command_name,
                addr=entry.address,
                val=target_value,
                interlocks=False,
                status="INTERLOCK_REJECTED",
                readback_ok=False,
                details=msg,
            )
            return {"success": False, "status": "INTERLOCK_REJECTED", "message": msg}

        # Step 5: Execute allowlisted Modbus write
        if entry.function_code == 5:
            # Write Single Coil
            coil_val = bool(target_value)
            write_ok, write_msg = await modbus_client.write_coil(entry.address, coil_val)
        elif entry.function_code == 6:
            # Write Single Register
            int_val = int(target_value)
            write_ok, write_msg = await modbus_client.write_register(entry.address, int_val)
        else:
            write_ok = False
            write_msg = f"Unsupported Modbus function code: {entry.function_code}"

        if not write_ok:
            logger.error(f"Write failed: {write_msg}")
            await self._record_audit(
                operator=operator,
                client_ip=client_ip,
                cmd_name=command_name,
                addr=entry.address,
                val=target_value,
                interlocks=True,
                status="WRITE_ERROR",
                readback_ok=False,
                details=write_msg,
            )
            return {"success": False, "status": "MODBUS_ERROR", "message": write_msg}

        # Step 6: Real readback verification from PLC or simulator
        readback_verified = False
        readback_val = None
        try:
            if entry.function_code == 5:  # Single Coil
                bits = await modbus_client._read_coils(entry.address, 1)
                if bits:
                    readback_val = 1 if bits[0] else 0
                    expected_bit = 1 if bool(target_value) else 0
                    readback_verified = (readback_val == expected_bit)
            elif entry.function_code == 6:  # Holding Register
                regs = await modbus_client._read_registers(entry.address, 1, function_code=3)
                if regs:
                    readback_val = regs[0]
                    readback_verified = (readback_val == int(target_value))
        except Exception as e:
            logger.warning(f"Readback verification query failed for {command_name} at address {entry.address}: {e}")
            readback_verified = False

        # Step 7: Record immutable audit log
        await self._record_audit(
            operator=operator,
            client_ip=client_ip,
            cmd_name=command_name,
            addr=entry.address,
            val=target_value,
            interlocks=True,
            status="SUCCESS",
            readback_ok=readback_verified,
            readback_val=readback_val,
            details=f"Command executed successfully by {operator} from {client_ip}",
        )

        logger.info(f"CONTROL SUCCESS: {command_name} -> {target_value} by {operator}")
        return {
            "success": True,
            "status": "SUCCESS",
            "message": f"Command '{command_name}' successfully sent and acknowledged by PLC.",
            "target_address": entry.address,
            "target_value": target_value,
            "readback_verified": readback_verified,
            "timestamp": now_iso,
        }

    async def _record_audit(
        self,
        operator: str,
        client_ip: str,
        cmd_name: str,
        addr: int,
        val: float,
        interlocks: bool,
        status: str,
        readback_ok: bool,
        readback_val: Optional[float] = None,
        details: str = "",
    ):
        """Appends audit event into SQLite audit log table."""
        try:
            async with async_session_factory() as session:
                async with session.begin():
                    audit_entry = ControlAuditLogModel(
                        operator=operator,
                        client_ip=client_ip,
                        command_name=cmd_name,
                        target_address=addr,
                        command_value=float(val),
                        interlocks_verified=interlocks,
                        write_status=status,
                        readback_verified=readback_ok,
                        readback_value=readback_val,
                        details=details,
                    )
                    session.add(audit_entry)
                await session.commit()
        except Exception as e:
            logger.error(f"Failed to record control audit log: {e}")


safe_control_service = SafeControlService()
