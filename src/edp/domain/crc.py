"""CRC-16/XMODEM (poly 0x1021, init 0x0000, sem reflexao/final-xor).

Usado pelos descritores UDF (campo DescriptorCRC do tag ECMA-167).
"""

from typing import Optional

_POLY = 0x1021


def _build_table():
    table = []
    for i in range(256):
        crc = i << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ _POLY) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
        table.append(crc)
    return tuple(table)


_TABLE = _build_table()


def crc16_xmodem(data, length: Optional[int] = None) -> int:
    """Retorna o CRC-16/XMODEM dos primeiros ``length`` bytes de ``data``."""
    if length is None:
        length = len(data)
    if length < 0 or length > len(data):
        raise ValueError("length fora dos limites de data")
    crc = 0
    for i in range(length):
        crc = ((crc << 8) & 0xFFFF) ^ _TABLE[((crc >> 8) ^ data[i]) & 0xFF]
    return crc
