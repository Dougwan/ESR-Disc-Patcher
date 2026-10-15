import unittest

from edp.domain import constants as C
from edp.iso.device import MemoryDevice
from edp.iso.udf import find_volume_recognition, looks_patched

from .fixtures import build_synthetic_iso


class UdfDetectionTests(unittest.TestCase):
    def test_finds_nsr(self):
        device = MemoryDevice(build_synthetic_iso())
        info = find_volume_recognition(device)
        self.assertIsNotNone(info)
        self.assertEqual(info.standard, "NSR02")

    def test_no_udf_on_zero_image(self):
        device = MemoryDevice(bytes(64 * C.SECTOR_SIZE))
        self.assertIsNone(find_volume_recognition(device))

    def test_not_patched_initially(self):
        device = MemoryDevice(build_synthetic_iso())
        self.assertFalse(looks_patched(device))

    def test_marker_detected(self):
        data = bytearray(build_synthetic_iso())
        offset = C.PATCH_MARKER_LBA * C.SECTOR_SIZE + C.PATCH_MARKER_OFFSET
        data[offset:offset + 4] = C.PATCH_MARKER
        self.assertTrue(looks_patched(MemoryDevice(bytes(data))))


if __name__ == "__main__":
    unittest.main()
