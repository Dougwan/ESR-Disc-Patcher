import unittest

from edp.domain.crc import crc16_xmodem


class Crc16XmodemTests(unittest.TestCase):
    def test_known_vector(self):
        # Vetor classico CRC-16/XMODEM
        self.assertEqual(crc16_xmodem(b"123456789"), 0x31C3)

    def test_empty_is_zero(self):
        self.assertEqual(crc16_xmodem(b""), 0)

    def test_leading_zero_byte(self):
        self.assertEqual(crc16_xmodem(b"\x00"), 0)

    def test_length_limit(self):
        full = crc16_xmodem(b"\x01\x02\x03\x04")
        limited = crc16_xmodem(b"\x01\x02\x03\x04", 3)
        self.assertEqual(limited, crc16_xmodem(b"\x01\x02\x03"))
        self.assertNotEqual(full, limited)

    def test_length_out_of_range(self):
        with self.assertRaises(ValueError):
            crc16_xmodem(b"\x01", 5)
        with self.assertRaises(ValueError):
            crc16_xmodem(b"\x01", -1)


if __name__ == "__main__":
    unittest.main()
