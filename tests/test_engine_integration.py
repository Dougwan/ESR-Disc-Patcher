import unittest

from edp.domain import constants as C
from edp.domain.errors import (
    AlreadyPatchedError,
    IsoStructureError,
    NotPatchedError,
    NotUdfError,
)
from edp.iso.device import MemoryDevice
from edp.iso.inspector import IsoInspector
from edp.iso.udf import looks_patched
from edp.patcher.dvd_data import load_dvd_video_data
from edp.patcher.engine import EsrPatchEngine

from .fixtures import TARGET_LBAS, build_synthetic_iso


class EngineIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.original = build_synthetic_iso()

    def _device(self):
        return MemoryDevice(self.original)

    # -- inspecao ---------------------------------------------------------
    def test_analysis_clean_image(self):
        analysis = IsoInspector(self._device()).analyze()
        self.assertTrue(analysis.is_udf)
        self.assertFalse(analysis.is_patched)
        self.assertEqual(analysis.patch_state, "clean")
        self.assertEqual(analysis.game_id, "SLUS_203.12")
        self.assertEqual(analysis.region, "NTSC-U")
        self.assertIsNotNone(analysis.elf)
        self.assertEqual(analysis.elf_problems, [])
        self.assertIsNotNone(analysis.system_cnf)

    # -- patch ------------------------------------------------------------
    def test_patch_applies_all_changes(self):
        device = self._device()
        engine = EsrPatchEngine(device)
        original_descriptors = {
            lba: self.original[lba * C.SECTOR_SIZE:(lba + 1) * C.SECTOR_SIZE]
            for lba in TARGET_LBAS
        }

        report = engine.patch(image_path="mem")
        self.assertEqual(report.action, "patch")
        self.assertTrue(looks_patched(device))

        # descritores reescritos apontam para o LBA 128
        for lba, backup in C.TARGET_DESCRIPTORS:
            block = device.read_at(lba * C.SECTOR_SIZE, C.SECTOR_SIZE)
            self.assertEqual(block[188], 128)
            self.assertEqual(block[189], 0)
            # backup preserva o original
            backup_block = device.read_at(backup * C.SECTOR_SIZE, C.SECTOR_SIZE)
            self.assertEqual(backup_block, original_descriptors[lba])

        # blob DVD-Video gravado no LBA 128
        dvd = device.read_at(C.DVD_VIDEO_LBA * C.SECTOR_SIZE, C.DVD_VIDEO_SIZE)
        self.assertEqual(dvd, load_dvd_video_data())

    def test_patch_reports_state(self):
        device = self._device()
        EsrPatchEngine(device).patch()
        analysis = IsoInspector(device).analyze()
        self.assertTrue(analysis.is_patched)
        self.assertEqual(analysis.patch_state, "patched")

    def test_patch_twice_raises(self):
        device = self._device()
        EsrPatchEngine(device).patch()
        with self.assertRaises(AlreadyPatchedError):
            EsrPatchEngine(device).patch()

    # -- unpatch ----------------------------------------------------------
    def test_unpatch_restores_original(self):
        device = self._device()
        engine = EsrPatchEngine(device)
        engine.patch()
        report = engine.unpatch(image_path="mem")
        self.assertEqual(report.action, "unpatch")
        self.assertFalse(looks_patched(device))
        # descritores restaurados byte a byte
        for lba in TARGET_LBAS:
            restored = device.read_at(lba * C.SECTOR_SIZE, C.SECTOR_SIZE)
            original = self.original[lba * C.SECTOR_SIZE:(lba + 1) * C.SECTOR_SIZE]
            self.assertEqual(restored, original)
        # area DVD zerada
        dvd = device.read_at(C.DVD_VIDEO_LBA * C.SECTOR_SIZE, C.DVD_VIDEO_SIZE)
        self.assertEqual(dvd, bytes(C.DVD_VIDEO_SIZE))
        # backups zerados
        self.assertEqual(
            device.read_at(C.PATCH_MARKER_LBA * C.SECTOR_SIZE, C.SECTOR_SIZE),
            bytes(C.SECTOR_SIZE),
        )

    def test_unpatch_when_clean_raises(self):
        with self.assertRaises(NotPatchedError):
            EsrPatchEngine(self._device()).unpatch()

    # -- validacoes -------------------------------------------------------
    def test_patch_rejects_non_udf(self):
        device = MemoryDevice(build_synthetic_iso(udf=False))
        with self.assertRaises(NotUdfError):
            EsrPatchEngine(device).patch()

    def test_patch_rejects_tiny_image(self):
        device = MemoryDevice(bytes(1024))
        with self.assertRaises(IsoStructureError):
            EsrPatchEngine(device).patch()

    # -- determinismo -----------------------------------------------------
    def test_patch_is_deterministic(self):
        dev_a = self._device()
        dev_b = self._device()
        EsrPatchEngine(dev_a).patch()
        EsrPatchEngine(dev_b).patch()
        self.assertEqual(dev_a.to_bytes(), dev_b.to_bytes())

    def test_deterministic_golden_bytes(self):
        """Golden: o byte alterado no descritor e exatamente o extent location."""
        device = self._device()
        EsrPatchEngine(device).patch()
        patched = device.to_bytes()
        for lba in TARGET_LBAS:
            off = lba * C.SECTOR_SIZE
            for i in range(C.SECTOR_SIZE):
                expected = self.original[off + i]
                if i in (188, 189):
                    expected = 128 if i == 188 else 0
                elif i in (4, 8, 9):
                    expected = patched[off + i]  # derivado do CRC/checksum
                self.assertEqual(patched[off + i], expected)


if __name__ == "__main__":
    unittest.main()
