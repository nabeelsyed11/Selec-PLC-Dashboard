"""
Industrial Modbus Register Decoder and Encoder
Supports 16-bit and 32-bit integers, IEEE-754 floating point,
and word/byte endianness transformations (Big Endian, Little Endian, Word Swap).
"""
import struct
from typing import List, Union, Optional


def decode_16bit_uint(registers: List[int], index: int = 0, byte_order: str = "big") -> int:
    """Decode 16-bit unsigned integer from register list."""
    if len(registers) <= index:
        raise ValueError(f"Insufficient registers to decode uint16 at index {index}")
    val = registers[index] & 0xFFFF
    if byte_order.lower() == "little":
        val = ((val & 0xFF) << 8) | ((val >> 8) & 0xFF)
    return val


def decode_16bit_int(registers: List[int], index: int = 0, byte_order: str = "big") -> int:
    """Decode 16-bit signed integer (two's complement)."""
    raw_uint = decode_16bit_uint(registers, index, byte_order)
    # Convert to signed int16
    return struct.unpack(">h" if byte_order.lower() == "big" else "<h", struct.pack(">H", raw_uint))[0]


def decode_32bit_uint(
    registers: List[int], index: int = 0, byte_order: str = "big", word_swap: bool = False
) -> int:
    """
    Decode 32-bit unsigned integer spanning 2 consecutive 16-bit registers.
    word_swap=False (ABCD or DCBA depending on byte_order)
    word_swap=True (CDAB or BADC)
    """
    if len(registers) < index + 2:
        raise ValueError(f"Requires at least 2 registers to decode uint32 at index {index}")

    r1, r2 = registers[index] & 0xFFFF, registers[index + 1] & 0xFFFF
    if word_swap:
        r1, r2 = r2, r1

    raw_bytes = struct.pack(">HH", r1, r2)
    fmt = ">I" if byte_order.lower() == "big" else "<I"
    return struct.unpack(fmt, raw_bytes)[0]


def decode_32bit_int(
    registers: List[int], index: int = 0, byte_order: str = "big", word_swap: bool = False
) -> int:
    """Decode 32-bit signed integer spanning 2 consecutive 16-bit registers."""
    if len(registers) < index + 2:
        raise ValueError(f"Requires at least 2 registers to decode int32 at index {index}")

    r1, r2 = registers[index] & 0xFFFF, registers[index + 1] & 0xFFFF
    if word_swap:
        r1, r2 = r2, r1

    raw_bytes = struct.pack(">HH", r1, r2)
    fmt = ">i" if byte_order.lower() == "big" else "<i"
    return struct.unpack(fmt, raw_bytes)[0]


def decode_32bit_float(
    registers: List[int], index: int = 0, byte_order: str = "big", word_swap: bool = False
) -> float:
    """Decode 32-bit IEEE-754 floating point number spanning 2 consecutive 16-bit registers."""
    if len(registers) < index + 2:
        raise ValueError(f"Requires at least 2 registers to decode float32 at index {index}")

    r1, r2 = registers[index] & 0xFFFF, registers[index + 1] & 0xFFFF
    if word_swap:
        r1, r2 = r2, r1

    raw_bytes = struct.pack(">HH", r1, r2)
    fmt = ">f" if byte_order.lower() == "big" else "<f"
    val = struct.unpack(fmt, raw_bytes)[0]
    return float(val)


def decode_signal(
    registers: List[int],
    data_type: str,
    index: int = 0,
    byte_order: str = "big",
    word_swap: bool = False,
    scaling_factor: float = 1.0,
    offset: float = 0.0,
) -> Union[int, float]:
    """
    Generic decode function given data_type and scaling parameters.
    Returns scaled engineering value.
    """
    dt = data_type.lower()
    if dt in ("uint16", "word"):
        raw = decode_16bit_uint(registers, index, byte_order)
    elif dt in ("int16", "short"):
        raw = decode_16bit_int(registers, index, byte_order)
    elif dt in ("uint32", "dword"):
        raw = decode_32bit_uint(registers, index, byte_order, word_swap)
    elif dt in ("int32", "dint"):
        raw = decode_32bit_int(registers, index, byte_order, word_swap)
    elif dt in ("float32", "float", "real"):
        raw = decode_32bit_float(registers, index, byte_order, word_swap)
    else:
        raise ValueError(f"Unsupported data type: {data_type}")

    # Apply scaling and offset: Value = (Raw * Scaling) + Offset
    scaled = (float(raw) * scaling_factor) + offset
    return scaled


def encode_16bit_uint(value: int, byte_order: str = "big") -> int:
    """Encode integer into 16-bit unsigned Modbus register format."""
    val = int(value) & 0xFFFF
    if byte_order.lower() == "little":
        val = ((val & 0xFF) << 8) | ((val >> 8) & 0xFF)
    return val


def encode_32bit_float(value: float, byte_order: str = "big", word_swap: bool = False) -> List[int]:
    """Encode 32-bit float into two 16-bit registers."""
    fmt = ">f" if byte_order.lower() == "big" else "<f"
    packed = struct.pack(fmt, float(value))
    r1, r2 = struct.unpack(">HH", packed)
    if word_swap:
        r1, r2 = r2, r1
    return [r1, r2]
