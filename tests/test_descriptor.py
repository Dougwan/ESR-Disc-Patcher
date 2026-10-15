import unittest

from edp.domain import constants as C
from edp.domain.crc import crc16_xmodem
from edp.domain.errors import IsoStructureError
from edp.patcher.descriptor import (
    patch_directory_descriptor,
    recompute_tag_checksums,
)

from .fixtures import make_descriptor_block


def _expected_crc(block):
    length = int.from_bytes(block[10:12], "little")
    return crc16_xmodem(block[16:16 + length])


def _expected_checksum(block):
    return (sum(block[0:16]) - block[4]) & 0xFF


class DescriptorTests(unittest.TestCase):
    def test_patch_sets_extent_location(self):
        original = make_descriptor_block(0x10)
        patched = patch_directory_descriptor(original, C.DVD_VIDEO_LBA)
        self.assertEqual(patched[188], 128)
        self.assertEqual(patched[189], 0)

    def test_patch_recomputes_crc_and_checksum(self):
        original = make_descriptor_block(0x10)
        patched = bytearray(patch_directory_descriptor(original, C.DVD_VIDEO_LBA))
        self.assertEqual(int.from_bytes(patched[8:10], "little"), _expected_crc(patched))
        self.assertEqual(patched[4], _expected_checksum(patched))

    def test_patch_is_idempotent(self):
        original = make_descriptor_block(0x10)
        once = patch_directory_descriptor(original, C.DVD_VIDEO_LBA)
        twice = patch_directory_descriptor(once, C.DVD_VIDEO_LBA)
        self.assertEqual(once, twice)

    def test_patch_preserves_unrelated_bytes(self):
        original = make_descriptor_block(0x10)
        patched = patch_directory_descriptor(original, C.DVD_VIDEO_LBA)
        # fora dos offsets alterados (4, 8, 9, 188, 189), o resto permanece
        changed = {4, 8, 9, 188, 189}
        for i in range(len(original)):
            if i not in changed:
                self.assertEqual(original[i], patched[i], "byte %d mudou" % i)

    def test_wrong_size_raises(self):
        with self.assertRaises(IsoStructureError):
            patch_directory_descriptor(b"\x00" * 100, 128)
        with self.assertRaises(IsoStructureError):
            recompute_tag_checksums(bytearray(10))

    def test_target_lba_out_of_range(self):
        with self.assertRaises(IsoStructureError):
            patch_directory_descriptor(make_descriptor_block(1), 0x10000)

    def test_recompute_matches_manual(self):
        block = bytearray(make_descriptor_block(0x42))
        block[8:10] = b"\x00\x00"
        block[4] = 0
        recompute_tag_checksums(block)
        self.assertEqual(int.from_bytes(block[8:10], "little"), _expected_crc(block))
        self.assertEqual(block[4], _expected_checksum(block))


if __name__ == "__main__":
    unittest.main()
