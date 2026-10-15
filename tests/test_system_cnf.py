import unittest

from edp.domain.system_cnf import parse_system_cnf


class SystemCnfTests(unittest.TestCase):
    def test_typical(self):
        text = "BOOT2 = cdrom0:\\SLUS_203.12;1\nVER = 1.00\nVMODE = NTSC\n"
        cnf = parse_system_cnf(text)
        self.assertEqual(cnf.boot_executable, "SLUS_203.12")
        self.assertEqual(cnf.entries["VER"], "1.00")
        self.assertEqual(cnf.entries["VMODE"], "NTSC")

    def test_forward_slashes_and_no_version(self):
        text = "boot2=cdrom0:/SLES_500.00\r\n"
        self.assertEqual(parse_system_cnf(text).boot_executable, "SLES_500.00")

    def test_comments_and_blank_lines(self):
        text = "\n// comentario\nBOOT2 = cdrom0:\\SCES_111.22;1 // inline\n"
        cnf = parse_system_cnf(text)
        self.assertEqual(cnf.boot_executable, "SCES_111.22")

    def test_missing_boot2(self):
        cnf = parse_system_cnf("VER = 2.00\n")
        self.assertIsNone(cnf.boot_executable)

    def test_bytes_input(self):
        cnf = parse_system_cnf(b"BOOT2 = cdrom0:\\SLPS_200.00;1\n")
        self.assertEqual(cnf.boot_executable, "SLPS_200.00")

    def test_ps1_boot_key(self):
        cnf = parse_system_cnf("BOOT = cdrom0:\\SCUS_945.00;1\n")
        self.assertEqual(cnf.boot_executable, "SCUS_945.00")


if __name__ == "__main__":
    unittest.main()
