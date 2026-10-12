"""
Register Map Parser and Configuration Loader
Validates signal specifications, polling groups, and writable allowlists.
"""
from pathlib import Path
from typing import Dict, List, Any, Optional
import yaml
from pydantic import BaseModel, Field


class DiscreteSignal(BaseModel):
    name: str
    description: str
    type: str = "discrete_input"  # discrete_input (FC 02) or coil (FC 01)
    address: int
    group: str = "fast_group"
    normal_state: int = 0
    debounce_ms: int = 50


class NumericalSignal(BaseModel):
    name: str
    description: str
    address: int
    register_count: int = 1
    function_code: int = 3
    data_type: str = "uint16"
    byte_order: str = "big"
    word_swap: bool = False
    scaling_factor: float = 1.0
    offset: float = 0.0
    engineering_unit: str = ""
    group: str = "fast_group"
    alarm_warning_high: Optional[float] = None
    alarm_critical_high: Optional[float] = None


class WritableAllowlistEntry(BaseModel):
    name: str
    address: int
    function_code: int
    description: str
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    requires_interlock: bool = True
    confirmation_required: bool = True


class PollingGroupConfig(BaseModel):
    interval_ms: int
    enabled: bool = True


class RegisterMapConfig(BaseModel):
    plc_connection: Dict[str, Any]
    polling_groups: Dict[str, PollingGroupConfig]
    writable_allowlist: List[WritableAllowlistEntry]
    discrete_signals: List[DiscreteSignal]
    numerical_signals: List[NumericalSignal]


def load_register_map(yaml_path: str) -> RegisterMapConfig:
    """Loads and validates the register map YAML."""
    path = Path(yaml_path)
    if not path.is_file():
        raise FileNotFoundError(f"Register map configuration file not found at: {yaml_path}")

    with open(path, "r", encoding="utf-8") as f:
        raw_data = yaml.safe_load(f)

    return RegisterMapConfig(**raw_data)


def group_contiguous_registers(signals: List[NumericalSignal], max_gap: int = 2) -> List[Dict[str, Any]]:
    """
    Groups individual numerical signals into contiguous blocks to minimize
    the number of Modbus TCP requests per polling cycle.
    """
    if not signals:
        return []

    # Sort signals by start register address
    sorted_signals = sorted(signals, key=lambda s: s.address)
    blocks = []
    current_block = {
        "start_address": sorted_signals[0].address,
        "count": sorted_signals[0].register_count,
        "function_code": sorted_signals[0].function_code,
        "signals": [sorted_signals[0]],
    }

    for sig in sorted_signals[1:]:
        curr_end = current_block["start_address"] + current_block["count"]
        # Same function code and adjacent or small gap
        if sig.function_code == current_block["function_code"] and (sig.address - curr_end) <= max_gap:
            new_end = sig.address + sig.register_count
            current_block["count"] = new_end - current_block["start_address"]
            current_block["signals"].append(sig)
        else:
            blocks.append(current_block)
            current_block = {
                "start_address": sig.address,
                "count": sig.register_count,
                "function_code": sig.function_code,
                "signals": [sig],
            }

    blocks.append(current_block)
    return blocks
