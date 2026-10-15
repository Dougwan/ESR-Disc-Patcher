"""Construtores de imagens sinteticas para os testes.

Nao usamos ISOs reais (grandes e com copyright): montamos em memoria uma
imagem minima que exercita os mesmos caminhos de codigo (VRS UDF, PVD ISO9660,
SYSTEM.CNF, ELF e os descritores-alvo do patch).
"""

import struct

SECTOR = 2048
TOTAL_SECTORS = 200

PVD_SECTOR = 16
BEA_SECTOR = 17
NSR_SECTOR = 18
TEA_SECTOR = 19
ROOT_SECTOR = 20
SYSTEM_CNF_SECTOR = 21
ELF_SECTOR = 22

TARGET_LBAS = (34, 50)


def make_elf32(machine=8, entry=0x00100000):
    ident = b"\x7fELF" + bytes([1, 1, 1, 0]) + b"\x00" * 8
    body = struct.pack(
        "<HHIIIIIHHHHHH",
        2, machine, 1, entry, 52, 0, 0x20924001, 52, 32, 1, 40, 0, 0,
    )
    return ident + body


def make_dir_record(name, lba, size, is_dir):
    rec_len = 33 + len(name)
    if rec_len % 2:
        rec_len += 1
    rec = bytearray(rec_len)
    rec[0] = rec_len
    rec[1] = 0
    rec[2:6] = lba.to_bytes(4, "little")
    rec[6:10] = lba.to_bytes(4, "big")
    rec[10:14] = size.to_bytes(4, "little")
    rec[14:18] = size.to_bytes(4, "big")
    rec[25] = 0x02 if is_dir else 0x00
    rec[32] = len(name)
    rec[33:33 + len(name)] = name
    return bytes(rec)


def make_descriptor_block(seed):
    block = bytearray(SECTOR)
    for i in range(SECTOR):
        block[i] = (seed + i * 7) & 0xFF
    block[10:12] = (256).to_bytes(2, "little")  # DescriptorCRCLength
    block[25:29] = b"+NSR"                       # marcador usado pelas ferramentas
    return bytes(block)


def _write(data, sector, payload):
    off = sector * SECTOR
    data[off:off + len(payload)] = payload


def build_synthetic_iso(
    udf=True,
    with_descriptors=True,
    system_cnf=(
        b"BOOT2 = cdrom0:\\SLUS_203.12;1\r\n"
        b"VER = 1.00\r\n"
        b"VMODE = NTSC\r\n"
    ),
    boot_name=b"SLUS_203.12;1",
    include_elf=True,
    with_pvd=True,
):
    """Monta uma imagem hibrida ISO9660/UDF minima."""
    data = bytearray(TOTAL_SECTORS * SECTOR)

    if udf:
        _write(data, BEA_SECTOR, b"\x00" + b"BEA01" + b"\x01\x00")
        _write(data, NSR_SECTOR, b"\x00" + b"NSR02" + b"\x01\x00")
        _write(data, TEA_SECTOR, b"\x00" + b"TEA01" + b"\x01\x00")

    if with_descriptors:
        for i, lba in enumerate(TARGET_LBAS):
            _write(data, lba, make_descriptor_block(0x10 + i))

    if with_pvd:
        pvd = bytearray(SECTOR)
        pvd[0] = 1
        pvd[1:6] = b"CD001"
        pvd[6] = 1
        vid = b"PS2_SYNTHETIC"
        pvd[40:40 + len(vid)] = vid
        pvd[156:190] = make_dir_record(b"\x00", ROOT_SECTOR, SECTOR, True)
        _write(data, PVD_SECTOR, bytes(pvd))

        root = bytearray(SECTOR)
        pos = 0
        for name, lba, size, is_dir in (
            (b"\x00", ROOT_SECTOR, SECTOR, True),
            (b"\x01", ROOT_SECTOR, SECTOR, True),
            (b"SYSTEM.CNF;1", SYSTEM_CNF_SECTOR, len(system_cnf), False),
            (boot_name, ELF_SECTOR, len(make_elf32()) if include_elf else 0, False),
        ):
            rec = make_dir_record(name, lba, size, is_dir)
            root[pos:pos + len(rec)] = rec
            pos += len(rec)
        _write(data, ROOT_SECTOR, bytes(root))

        if system_cnf is not None:
            _write(data, SYSTEM_CNF_SECTOR, system_cnf)
        if include_elf:
            _write(data, ELF_SECTOR, make_elf32())

    return bytes(data)
