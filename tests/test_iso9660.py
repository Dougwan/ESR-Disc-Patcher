import unittest

from edp.iso.device import MemoryDevice
from edp.iso.iso9660 import Iso9660Volume, read_pvd

from .fixtures import SYSTEM_CNF_SECTOR, build_synthetic_iso, make_elf32


class Iso9660Tests(unittest.TestCase):
    def setUp(self):
        self.device = MemoryDevice(build_synthetic_iso())
        self.volume = Iso9660Volume.open(self.device)

    def test_read_pvd(self):
        pvd = read_pvd(self.device)
        self.assertIsNotNone(pvd)
        self.assertEqual(pvd[0], 1)
        self.assertEqual(pvd[1:6], b"CD001")

    def test_volume_id(self):
        self.assertEqual(self.volume.volume_id, "PS2_SYNTHETIC")

    def test_list_root_names(self):
        names = {e.name.upper() for e in self.volume.list_root()}
        self.assertIn("SYSTEM.CNF", names)
        self.assertIn("SLUS_203.12", names)

    def test_find_and_read_system_cnf(self):
        entry = self.volume.find("system.cnf")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.lba, SYSTEM_CNF_SECTOR)
        content = self.volume.read_file(entry)
        self.assertIn(b"BOOT2", content)

    def test_read_prefix(self):
        entry = self.volume.find("SLUS_203.12")
        prefix = self.volume.read_prefix(entry, 64)
        self.assertEqual(prefix[:4], b"\x7fELF")
        self.assertEqual(len(prefix), 52)

    def test_no_pvd(self):
        device = MemoryDevice(build_synthetic_iso(with_pvd=False))
        self.assertIsNone(read_pvd(device))


if __name__ == "__main__":
    unittest.main()
