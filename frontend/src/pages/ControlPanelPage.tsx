import React, { useState, useEffect } from "react";
import { TelemetryMessage, WritableCommandSpec, ControlAuditLog } from "../types";
import { Shield, ShieldAlert, CheckCircle2, AlertOctagon, RotateCcw, Power, Play, Square, Sliders, Lock } from "lucide-react";

interface Props {
  telemetry: TelemetryMessage | null;
}

export const ControlPanelPage: React.FC<Props> = ({ telemetry }) => {
  const [allowlist, setAllowlist] = useState<WritableCommandSpec[]>([]);
  const [remoteGloballyEnabled, setRemoteGloballyEnabled] = useState<boolean>(false);
  const [operatorName, setOperatorName] = useState<string>("authorized_operator");
  const [auditLogs, setAuditLogs] = useState<ControlAuditLog[]>([]);
  
  // Confirmation Modal State
  const [pendingCommand, setPendingCommand] = useState<{ name: string; value: number; label: string } | null>(null);
  const [feedbackMsg, setFeedbackMsg] = useState<{ text: string; error: boolean } | null>(null);
  
  // Setpoint state
  const [speedSetpoint, setSpeedSetpoint] = useState<number>(400);

  useEffect(() => {
    fetchAllowlist();
    fetchAuditLogs();
  }, []);

  const fetchAllowlist = async () => {
    try {
      const res = await fetch("/api/control/allowlist");
      if (res.ok) {
        const data = await res.json();
        setAllowlist(data.allowlist);
        setRemoteGloballyEnabled(data.remote_control_globally_enabled);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchAuditLogs = async () => {
    try {
      const res = await fetch("/api/control/audit-logs");
      if (res.ok) {
        const data = await res.json();
        setAuditLogs(data.audit_logs || []);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleExecuteCommand = async (cmdName: string, val: number) => {
    setPendingCommand(null);
    setFeedbackMsg(null);
    try {
      const res = await fetch("/api/control/execute", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          command_name: cmdName,
          target_value: val,
          operator_name: operatorName,
          operator_confirmed: true,
        }),
      });
      const data = await res.json();
      if (res.ok && data.success) {
        setFeedbackMsg({ text: data.message, error: false });
      } else {
        setFeedbackMsg({ text: data.detail || data.message || "Command rejected", error: true });
      }
      fetchAuditLogs();
    } catch (e: any) {
      setFeedbackMsg({ text: e.message || "Network error", error: true });
    }
  };

  if (!telemetry) return null;
  const signals = telemetry.signals;
  const isSim = Boolean(telemetry.simulation_mode);
  const isConnected = Boolean(telemetry.plc_connected ?? telemetry.diagnostics?.connected);
  const hasHardwareAccess = isSim || isConnected;

  const eStopOk = signals.emergency_stop_ok?.value === 1;
  const guardClosed = signals.safety_guard_closed?.value === 1;
  const vfdFault = signals.vfd_fault_status?.value === 1;
  const pusherCmd = signals.pusher_command?.value === 1;
  const pusherExtFeedback = signals.pusher_extended_feedback?.value === 1;
  const pusherRetFeedback = signals.pusher_retracted_feedback?.value === 1;
  const vfdRunning = signals.vfd_running_status?.value === 1;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* Safety Header Banner */}
      <div
        className="glass-panel"
        style={{
          padding: "20px 24px",
          borderLeft: remoteGloballyEnabled ? "6px solid #f59e0b" : "6px solid #ef4444",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "16px" }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              {remoteGloballyEnabled ? (
                <Shield style={{ width: "22px", height: "22px", color: "#f59e0b" }} />
              ) : (
                <Lock style={{ width: "22px", height: "22px", color: "#ef4444" }} />
              )}
              <h2 style={{ fontSize: "20px", fontWeight: 700 }}>Safe Machine Remote Control Console</h2>
            </div>
            <p style={{ color: "var(--text-muted)", fontSize: "13px", marginTop: "4px" }}>
              Deterministic PLC output sequencing with strict allowlist and mechanical feedback verification
            </p>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>Control Policy:</span>
            {remoteGloballyEnabled ? (
              <span className="badge-quality-stale" style={{ padding: "4px 10px", borderRadius: "6px", fontSize: "12px", fontWeight: 700 }}>
                ENABLED FOR AUTHORIZED OPERATORS
              </span>
            ) : (
              <span className="badge-quality-disconnected" style={{ padding: "4px 10px", borderRadius: "6px", fontSize: "12px", fontWeight: 700 }}>
                DISABLED BY DEFAULT (SAFETY LOCK)
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Disconnection Safety Lockout Banner */}
      {!hasHardwareAccess && (
        <div
          style={{
            padding: "16px 20px",
            borderRadius: "8px",
            background: "rgba(239, 68, 68, 0.15)",
            border: "1px solid rgba(239, 68, 68, 0.4)",
            display: "flex",
            alignItems: "center",
            gap: "14px",
          }}
        >
          <AlertOctagon style={{ width: "24px", height: "24px", color: "#f87171", flexShrink: 0 }} />
          <div style={{ fontSize: "13px", lineHeight: "1.5" }}>
            <strong style={{ color: "#f87171", display: "block" }}>CRITICAL SAFETY LOCKOUT: Physical Selec PLC Not Detected</strong>
            Simulation is OFF and no physical connection is active at <code className="mono">{telemetry.plc_host || "192.168.1.50"}:{telemetry.plc_port || 502}</code>. All output coils (Pusher Solenoid, VFD Run/Stop) and speed setpoint registers are locked in safe offline state and cannot be commanded.
          </div>
        </div>
      )}

      {feedbackMsg && (
        <div
          style={{
            padding: "14px 18px",
            borderRadius: "8px",
            fontSize: "13px",
            display: "flex",
            alignItems: "center",
            gap: "10px",
            background: feedbackMsg.error ? "rgba(239, 68, 68, 0.15)" : "rgba(16, 185, 129, 0.15)",
            border: feedbackMsg.error ? "1px solid rgba(239, 68, 68, 0.3)" : "1px solid rgba(16, 185, 129, 0.3)",
            color: feedbackMsg.error ? "#f87171" : "#34d399",
          }}
        >
          {feedbackMsg.error ? <AlertOctagon style={{ width: "16px", height: "16px" }} /> : <CheckCircle2 style={{ width: "16px", height: "16px" }} />}
          {feedbackMsg.text}
        </div>
      )}

      {/* Hardware Permissive Interlocks Card */}
      <div className="glass-panel" style={{ padding: "20px 24px" }}>
        <h3 style={{ fontSize: "16px", fontWeight: 600, marginBottom: "16px" }}>Machine Safety Permissive Interlocks</h3>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px" }}>
          {/* E-Stop */}
          <div style={{ background: "rgba(0,0,0,0.3)", padding: "16px", borderRadius: "8px", display: "flex", alignItems: "center", gap: "12px" }}>
            <div style={{ width: "12px", height: "12px", borderRadius: "50%", backgroundColor: !hasHardwareAccess ? "#6b7280" : eStopOk ? "#34d399" : "#ef4444" }} />
            <div>
              <div style={{ fontSize: "13px", fontWeight: 600 }}>Emergency Stop Circuit</div>
              <div style={{ fontSize: "11px", color: !hasHardwareAccess ? "var(--text-muted)" : eStopOk ? "#34d399" : "#ef4444" }}>
                {!hasHardwareAccess ? "PLC OFFLINE (UNKNOWN)" : eStopOk ? "Closed / Healthy (Permissive OK)" : "TRIPPED / OPEN"}
              </div>
            </div>
          </div>

          {/* Safety Guard */}
          <div style={{ background: "rgba(0,0,0,0.3)", padding: "16px", borderRadius: "8px", display: "flex", alignItems: "center", gap: "12px" }}>
            <div style={{ width: "12px", height: "12px", borderRadius: "50%", backgroundColor: !hasHardwareAccess ? "#6b7280" : guardClosed ? "#34d399" : "#ef4444" }} />
            <div>
              <div style={{ fontSize: "13px", fontWeight: 600 }}>Safety Guard Door</div>
              <div style={{ fontSize: "11px", color: !hasHardwareAccess ? "var(--text-muted)" : guardClosed ? "#34d399" : "#ef4444" }}>
                {!hasHardwareAccess ? "PLC OFFLINE (UNKNOWN)" : guardClosed ? "Locked / Closed (Permissive OK)" : "OPEN (Interlock Locked)"}
              </div>
            </div>
          </div>

          {/* VFD Fault */}
          <div style={{ background: "rgba(0,0,0,0.3)", padding: "16px", borderRadius: "8px", display: "flex", alignItems: "center", gap: "12px" }}>
            <div style={{ width: "12px", height: "12px", borderRadius: "50%", backgroundColor: !hasHardwareAccess ? "#6b7280" : !vfdFault ? "#34d399" : "#ef4444" }} />
            <div>
              <div style={{ fontSize: "13px", fontWeight: 600 }}>VFD Drive Status</div>
              <div style={{ fontSize: "11px", color: !hasHardwareAccess ? "var(--text-muted)" : !vfdFault ? "#34d399" : "#ef4444" }}>
                {!hasHardwareAccess ? "PLC OFFLINE (UNKNOWN)" : !vfdFault ? "Ready / No Fault" : "DRIVE FAULT ACTIVE"}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Control Widgets Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "16px" }}>
        {/* Widget 1: Pusher Actuator */}
        <div className="glass-panel" style={{ padding: "20px" }}>
          <h4 style={{ fontSize: "15px", fontWeight: 600, marginBottom: "8px" }}>Pusher Solenoid Actuator</h4>
          <p style={{ fontSize: "12px", color: "var(--text-muted)", marginBottom: "16px" }}>
            PLC Coil 0 (Extend / Retract) with magnetic reed switch sensor verification
          </p>

          <div style={{ display: "flex", gap: "12px", marginBottom: "16px" }}>
            <button
              className="btn-primary"
              disabled={!hasHardwareAccess || !remoteGloballyEnabled || !eStopOk || !guardClosed}
              onClick={() => setPendingCommand({ name: "pusher_command", value: 1, label: "Extend Pusher Cylinder" })}
            >
              Extend Pusher
            </button>
            <button
              className="btn-secondary"
              disabled={!hasHardwareAccess || !remoteGloballyEnabled || !eStopOk || !guardClosed}
              onClick={() => setPendingCommand({ name: "pusher_command", value: 0, label: "Retract Pusher Cylinder" })}
            >
              Retract Pusher
            </button>
          </div>

          <div style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: "12px", display: "flex", flexDirection: "column", gap: "6px", fontSize: "12px" }}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span>Commanded Coil State:</span>
              <strong className="mono">{!hasHardwareAccess ? "OFFLINE" : pusherCmd ? "1 (EXTEND)" : "0 (RETRACT)"}</strong>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span>Extended Sensor Feedback:</span>
              <span className="mono" style={{ color: !hasHardwareAccess ? "var(--text-muted)" : pusherExtFeedback ? "#34d399" : "var(--text-muted)" }}>
                {!hasHardwareAccess ? "OFFLINE" : pusherExtFeedback ? "DETECTED (1)" : "0"}
              </span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span>Retracted Sensor Feedback:</span>
              <span className="mono" style={{ color: !hasHardwareAccess ? "var(--text-muted)" : pusherRetFeedback ? "#34d399" : "var(--text-muted)" }}>
                {!hasHardwareAccess ? "OFFLINE" : pusherRetFeedback ? "DETECTED (1)" : "0"}
              </span>
            </div>
          </div>
        </div>

        {/* Widget 2: VFD Run / Stop */}
        <div className="glass-panel" style={{ padding: "20px" }}>
          <h4 style={{ fontSize: "15px", fontWeight: 600, marginBottom: "8px" }}>VFD Conveyor Drive Control</h4>
          <p style={{ fontSize: "12px", color: "var(--text-muted)", marginBottom: "16px" }}>
            PLC Coil 1 (Run / Stop Command) and Speed Setpoint Holding Register
          </p>

          <div style={{ display: "flex", gap: "12px", marginBottom: "16px" }}>
            <button
              className="btn-primary"
              disabled={!hasHardwareAccess || !remoteGloballyEnabled || !eStopOk || !guardClosed || vfdRunning}
              onClick={() => setPendingCommand({ name: "vfd_run_command", value: 1, label: "Start VFD Conveyor Drive" })}
            >
              <Play style={{ width: "14px", height: "14px" }} /> Start Drive
            </button>
            <button
              className="btn-danger"
              disabled={!hasHardwareAccess || !remoteGloballyEnabled || !vfdRunning}
              onClick={() => setPendingCommand({ name: "vfd_run_command", value: 0, label: "Stop VFD Conveyor Drive" })}
            >
              <Square style={{ width: "14px", height: "14px" }} /> Stop Drive
            </button>
          </div>

          <div style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: "12px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", marginBottom: "8px" }}>
              <span>Speed Setpoint: <strong>{(speedSetpoint / 10).toFixed(1)} Hz</strong></span>
              <button
                className="btn-secondary"
                style={{ padding: "2px 8px", fontSize: "11px" }}
                disabled={!hasHardwareAccess || !remoteGloballyEnabled}
                onClick={() => setPendingCommand({ name: "vfd_speed_setpoint", value: speedSetpoint, label: `Set VFD Speed to ${(speedSetpoint / 10).toFixed(1)} Hz` })}
              >
                Apply Speed
              </button>
            </div>
            <input
              type="range"
              min={50}
              max={500}
              step={10}
              value={speedSetpoint}
              disabled={!hasHardwareAccess || !remoteGloballyEnabled}
              onChange={(e) => setSpeedSetpoint(Number(e.target.value))}
              style={{ width: "100%", accentColor: "var(--primary-cyan)" }}
            />
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "10px", color: "var(--text-dim)", marginTop: "4px" }}>
              <span>5.0 Hz (Min)</span>
              <span>50.0 Hz (Max Safe)</span>
            </div>
          </div>
        </div>
      </div>

      {/* Safety Confirmation Modal */}
      {pendingCommand && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(0,0,0,0.75)",
            backdropFilter: "blur(6px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 9999,
            padding: "20px",
          }}
        >
          <div className="glass-panel" style={{ maxWidth: "480px", width: "100%", padding: "24px", border: "1px solid var(--border-highlight)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px", color: "#f59e0b", marginBottom: "12px" }}>
              <AlertOctagon style={{ width: "24px", height: "24px" }} />
              <h3 style={{ fontSize: "18px", fontWeight: 700 }}>Confirm Consequential Action</h3>
            </div>
            <p style={{ fontSize: "14px", color: "var(--text-main)", lineHeight: 1.5, marginBottom: "16px" }}>
              You are requesting to: <strong>{pendingCommand.label}</strong>.
            </p>
            <div style={{ background: "rgba(0,0,0,0.3)", padding: "12px", borderRadius: "8px", fontSize: "12px", color: "var(--text-muted)", marginBottom: "20px" }}>
              Operator: <strong style={{ color: "var(--text-main)" }}>{operatorName}</strong><br />
              Target Register: <span className="mono">{pendingCommand.name}</span><br />
              Target Value: <span className="mono">{pendingCommand.value}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "flex-end", gap: "12px" }}>
              <button className="btn-secondary" onClick={() => setPendingCommand(null)}>
                Cancel
              </button>
              <button
                className="btn-primary"
                onClick={() => handleExecuteCommand(pendingCommand.name, pendingCommand.value)}
              >
                Confirm & Dispatch
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Control Audit Log Table */}
      <div className="glass-panel" style={{ padding: "20px 24px" }}>
        <h3 style={{ fontSize: "16px", fontWeight: 600, marginBottom: "16px" }}>Immutable Control Audit Trail</h3>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: "12px" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border-subtle)", color: "var(--text-muted)" }}>
                <th style={{ padding: "8px 12px" }}>Timestamp</th>
                <th style={{ padding: "8px 12px" }}>Operator</th>
                <th style={{ padding: "8px 12px" }}>Command</th>
                <th style={{ padding: "8px 12px" }}>Value</th>
                <th style={{ padding: "8px 12px" }}>Status</th>
                <th style={{ padding: "8px 12px" }}>Readback</th>
              </tr>
            </thead>
            <tbody>
              {auditLogs.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ padding: "20px", textAlign: "center", color: "var(--text-dim)" }}>
                    No audit records logged yet.
                  </td>
                </tr>
              ) : (
                auditLogs.map((log) => (
                  <tr key={log.id} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                    <td className="mono" style={{ padding: "10px 12px" }}>{log.timestamp}</td>
                    <td style={{ padding: "10px 12px", fontWeight: 500 }}>{log.operator}</td>
                    <td style={{ padding: "10px 12px", color: "var(--primary-cyan)" }}>{log.command_name}</td>
                    <td className="mono" style={{ padding: "10px 12px" }}>{log.command_value}</td>
                    <td style={{ padding: "10px 12px" }}>
                      <span className="mono" style={{ color: log.status === "SUCCESS" ? "#34d399" : "#f87171" }}>
                        {log.status}
                      </span>
                    </td>
                    <td className="mono" style={{ padding: "10px 12px" }}>
                      {log.readback_verified ? "VERIFIED" : "--"}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
