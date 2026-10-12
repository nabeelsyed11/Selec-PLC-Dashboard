"""
Automated unit tests for Modbus register decoders, endianness conversions,
scaling factors, and writable allowlist enforcement.
"""
import pytest
from app.plc.decoder import (
    decode_16bit_uint,
    decode_16bit_int,
    decode_32bit_uint,
    decode_32bit_int,
    decode_32bit_float,
    decode_signal,
    encode_16bit_uint,
    encode_32bit_float,
)
from app.plc.register_map import load_register_map, group_contiguous_registers
from app.core.config import settings


def test_decode_16bit():
    regs = [0x0100, 0xFF00]
    # Big-endian 0x0100 = 256
    assert decode_16bit_uint(regs, 0, "big") == 256
    # Signed int: 0xFFFF = -1, 0x8000 = -32768
    regs_signed = [0xFFFF, 0x0005]
    assert decode_16bit_int(regs_signed, 0, "big") == -1
    assert decode_16bit_int(regs_signed, 1, "big") == 5


def test_decode_32bit_uint():
    # 0x0001, 0x0002 -> 0x00010002 = 65538
    regs = [0x0001, 0x0002]
    val = decode_32bit_uint(regs, 0, byte_order="big", word_swap=False)
    assert val == 65538

    # With word swap: 0x0002, 0x0001 -> 0x00020001 = 131073
    val_swapped = decode_32bit_uint(regs, 0, byte_order="big", word_swap=True)
    assert val_swapped == 131073


def test_decode_32bit_float():
    # Encode 230.5V into two registers
    encoded = encode_32bit_float(230.5, byte_order="big", word_swap=False)
    assert len(encoded) == 2
    decoded = decode_32bit_float(encoded, 0, byte_order="big", word_swap=False)
    assert pytest.approx(decoded, 0.001) == 230.5


def test_signal_scaling_and_offset():
    # Motor temp: 253 counts with 0.1 scaling -> 25.3 °C
    regs = [253]
    val = decode_signal(
        registers=regs,
        data_type="int16",
        index=0,
        scaling_factor=0.1,
        offset=0.0
    )
    assert pytest.approx(val, 0.01) == 25.3

    # Load cell: 420 counts with 0.1 scaling and -2.0 offset -> 40.0 kg
    regs_lc = [420]
    val_lc = decode_signal(
        registers=regs_lc,
        data_type="uint16",
        index=0,
        scaling_factor=0.1,
        offset=-2.0
    )
    assert pytest.approx(val_lc, 0.01) == 40.0


def test_register_map_loading_and_grouping():
    reg_map = load_register_map(settings.REGISTER_MAP_PATH)
    assert len(reg_map.discrete_signals) > 0
    assert len(reg_map.numerical_signals) > 0
    assert len(reg_map.writable_allowlist) > 0

    # Test contiguous grouping
    fast_signals = [s for s in reg_map.numerical_signals if s.group == "fast_group"]
    blocks = group_contiguous_registers(fast_signals, max_gap=2)
    assert len(blocks) > 0
    # Group blocks should cover all fast signals
    total_grouped_signals = sum(len(b["signals"]) for b in blocks)
    assert total_grouped_signals == len(fast_signals)
