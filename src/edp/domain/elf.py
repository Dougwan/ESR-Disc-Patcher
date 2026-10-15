"""Parsing e validacao do cabecalho ELF (foco em ELF de PS2: MIPS32 LE)."""

import struct
from typing import List

from .errors import ElfFormatError
from .models import ElfHeader

ELF_MAGIC = b"\x7fELF"
ELFCLASS32 = 1
ELFCLASS64 = 2
ELFDATA2LSB = 1
ELFDATA2MSB = 2
EM_MIPS = 8

_HEADER32_MIN = 52
_HEADER64_MIN = 64


def parse_elf_header(data) -> ElfHeader:
    """Le o cabecalho ELF a partir dos bytes informados."""
    if len(data) < 16:
        raise ElfFormatError("dados insuficientes para o identificador ELF")
    if data[:4] != ELF_MAGIC:
        raise ElfFormatError("magic ELF invalido")

    elf_class = data[4]
    data_encoding = data[5]

    if data_encoding == ELFDATA2LSB:
        endian = "<"
    elif data_encoding == ELFDATA2MSB:
        endian = ">"
    else:
        raise ElfFormatError("encoding de dados ELF desconhecido: %r" % data_encoding)

    if elf_class == ELFCLASS32:
        if len(data) < _HEADER32_MIN:
            raise ElfFormatError("cabecalho ELF32 truncado")
        fmt = endian + "HHIIIIIHHHHHH"
        (e_type, e_machine, e_version, e_entry, e_phoff, e_shoff, e_flags,
         e_ehsize, e_phentsize, e_phnum, e_shentsize, e_shnum,
         e_shstrndx) = struct.unpack_from(fmt, data, 16)
    elif elf_class == ELFCLASS64:
        if len(data) < _HEADER64_MIN:
            raise ElfFormatError("cabecalho ELF64 truncado")
        fmt = endian + "HHIQQQIHHHHHH"
        (e_type, e_machine, e_version, e_entry, e_phoff, e_shoff, e_flags,
         e_ehsize, e_phentsize, e_phnum, e_shentsize, e_shnum,
         e_shstrndx) = struct.unpack_from(fmt, data, 16)
    else:
        raise ElfFormatError("classe ELF desconhecida: %r" % elf_class)

    return ElfHeader(
        elf_class=elf_class,
        data_encoding=data_encoding,
        machine=e_machine,
        entry=e_entry,
        phoff=e_phoff,
        phnum=e_phnum,
        shoff=e_shoff,
        shnum=e_shnum,
    )


def validate_ps2_elf(header: ElfHeader) -> List[str]:
    """Retorna uma lista de problemas (vazia se for um ELF de PS2 plausivel)."""
    problems: List[str] = []
    if not header.is_32bit:
        problems.append("ELF nao e 32-bit (PS2 EE usa ELFCLASS32)")
    if not header.is_little_endian:
        problems.append("ELF nao e little-endian (PS2 EE usa ELFDATA2LSB)")
    if not header.is_mips:
        problems.append("e_machine != MIPS (%d)" % header.machine)
    if header.entry == 0:
        problems.append("entry point nulo")
    if header.phnum == 0:
        problems.append("sem program headers (e_phnum == 0)")
    return problems
