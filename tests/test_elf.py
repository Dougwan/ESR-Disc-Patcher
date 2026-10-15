import struct
import unittest

from edp.domain.elf import parse_elf_header, validate_ps2_elf
from edp.domain.errors import ElfFormatError

from .fixtures import make_elf32


class ElfHeaderTests(unittest.TestCase):
    def test_parse_valid_mips32_le(self):
        header = parse_elf_header(make_elf32(entry=0x00123456))
        self.assertTrue(header.is_32bit)
        self.assertTrue(header.is_little_endian)
        self.assertTrue(header.is_mips)
        self.assertEqual(header.entry, 0x00123456)
        self.assertEqual(header.phnum, 1)

    def test_validate_ps2_elf_ok(self):
        self.assertEqual(validate_ps2_elf(parse_elf_header(make_elf32())), [])

    def test_validate_flags_wrong_machine(self):
        header = parse_elf_header(make_elf32(machine=3))  # x86
        problems = validate_ps2_elf(header)
        self.assertTrue(any("MIPS" in p for p in problems))

    def test_validate_flags_64bit_big_endian(self):
        ident = b"\x7fELF" + bytes([2, 2, 1, 0]) + b"\x00" * 8
        body = struct.pack("<HHIQQQIHHHHHH", 2, 8, 1, 0x100000, 64, 0,
                           0, 64, 56, 1, 64, 0, 0)
        header = parse_elf_header(ident + body)
        problems = validate_ps2_elf(header)
        self.assertTrue(any("32-bit" in p for p in problems))
        self.assertTrue(any("little-endian" in p for p in problems))

    def test_bad_magic(self):
        with self.assertRaises(ElfFormatError):
            parse_elf_header(b"NOTELF" + b"\x00" * 60)

    def test_truncated(self):
        with self.assertRaises(ElfFormatError):
            parse_elf_header(b"\x7fELF\x01\x01")

    def test_unknown_encoding(self):
        data = b"\x7fELF" + bytes([1, 9]) + b"\x00" * 60
        with self.assertRaises(ElfFormatError):
            parse_elf_header(data)


if __name__ == "__main__":
    unittest.main()
