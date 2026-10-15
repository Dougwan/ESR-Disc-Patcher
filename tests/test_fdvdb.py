import os
import shutil
import tempfile
import unittest

from edp.domain import constants as C
from edp.domain.errors import FdvdbError, PathError
from edp.iso.device import MemoryDevice
from edp.patcher.engine import EsrPatchEngine
from edp.patcher.fdvdb import (
    LOADER_OFFSET,
    VIDEO_TS_IFO_OFFSET,
    VIDEO_TS_IFO_SIZE,
    VTS_01_0_IFO_OFFSET,
    VTS_01_0_IFO_SIZE,
    apply_fdvdb_overlay,
)
from edp.patcher.service import EsrService

from .fixtures import build_synthetic_iso

_VIDEO_TS_IFO = bytes([0x0A]) * VIDEO_TS_IFO_SIZE
_VTS_01_0_IFO = bytes([0x0B]) * VTS_01_0_IFO_SIZE
_LOADER = b"\x7fELF" + bytes([0x5C]) * 4096


class FdvdbOverlayTests(unittest.TestCase):
    def _esr_patched_device(self):
        device = MemoryDevice(build_synthetic_iso())
        EsrPatchEngine(device).patch()
        return device

    def test_overlay_places_payloads(self):
        device = self._esr_patched_device()
        report = apply_fdvdb_overlay(device, _VIDEO_TS_IFO, _VTS_01_0_IFO, _LOADER)
        self.assertEqual(report.video_ts_ifo_size, VIDEO_TS_IFO_SIZE)
        self.assertEqual(report.vts_01_0_ifo_size, VTS_01_0_IFO_SIZE)
        self.assertEqual(report.name_renames, 1)
        self.assertEqual(report.ad_rewrites, 2)

        self.assertEqual(device.read_at(VIDEO_TS_IFO_OFFSET, VIDEO_TS_IFO_SIZE), _VIDEO_TS_IFO)
        self.assertEqual(device.read_at(VTS_01_0_IFO_OFFSET, VTS_01_0_IFO_SIZE), _VTS_01_0_IFO)
        self.assertEqual(device.read_at(LOADER_OFFSET, len(_LOADER)), _LOADER)

    def test_overlay_renames_and_rewrites_short_ads(self):
        device = self._esr_patched_device()
        apply_fdvdb_overlay(device, _VIDEO_TS_IFO, _VTS_01_0_IFO, _LOADER)
        region = device.read_at(0, VIDEO_TS_IFO_OFFSET)
        self.assertNotIn(b"VIDEO_TS.BUP", region)
        self.assertIn(b"VTS_01_0.IFO", region)
        self.assertIn(bytes.fromhex("003800000a00"), region)
        self.assertIn(bytes.fromhex("003000001100"), region)

    def test_overlay_requires_esr_patched(self):
        device = MemoryDevice(build_synthetic_iso())  # sem ESR patch
        with self.assertRaises(FdvdbError):
            apply_fdvdb_overlay(device, _VIDEO_TS_IFO, _VTS_01_0_IFO, _LOADER)

    def test_wrong_payload_sizes(self):
        device = self._esr_patched_device()
        with self.assertRaises(FdvdbError):
            apply_fdvdb_overlay(device, b"x" * 10, _VTS_01_0_IFO, _LOADER)
        with self.assertRaises(FdvdbError):
            apply_fdvdb_overlay(device, _VIDEO_TS_IFO, b"x" * 10, _LOADER)
        with self.assertRaises(FdvdbError):
            apply_fdvdb_overlay(device, _VIDEO_TS_IFO, _VTS_01_0_IFO, b"")


class FdvdbServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="edp_fdvdb_")
        self.src = os.path.join(self.tmp, "game.iso")
        with open(self.src, "wb") as fh:
            fh.write(build_synthetic_iso())
        self.vt = os.path.join(self.tmp, "VIDEO_TS.IFO")
        self.v1 = os.path.join(self.tmp, "VTS_01_0.IFO")
        self.ld = os.path.join(self.tmp, "loader.elf")
        for path, data in ((self.vt, _VIDEO_TS_IFO), (self.v1, _VTS_01_0_IFO), (self.ld, _LOADER)):
            with open(path, "wb") as fh:
                fh.write(data)

    def tearDown(self):
        for name in os.listdir(self.tmp):
            os.remove(os.path.join(self.tmp, name))
        os.rmdir(self.tmp)

    def test_make_fdvdb_image_end_to_end(self):
        dst = os.path.join(self.tmp, "game_fdvdb.iso")
        report = EsrService().make_fdvdb_image(
            self.src, dst, self.vt, self.v1, self.ld
        )
        self.assertEqual(report.loader_size, len(_LOADER))
        self.assertTrue(os.path.isfile(dst))

        with open(dst, "rb") as fh:
            blob = fh.read()
        self.assertGreaterEqual(len(blob), LOADER_OFFSET + len(_LOADER))
        self.assertEqual(
            blob[VIDEO_TS_IFO_OFFSET:VIDEO_TS_IFO_OFFSET + VIDEO_TS_IFO_SIZE], _VIDEO_TS_IFO
        )
        self.assertEqual(
            blob[LOADER_OFFSET:LOADER_OFFSET + len(_LOADER)], _LOADER
        )
        # ESR permanece aplicado (marcador +NSR na copia de backup)
        self.assertEqual(
            blob[C.PATCH_MARKER_LBA * C.SECTOR_SIZE + C.PATCH_MARKER_OFFSET:
                 C.PATCH_MARKER_LBA * C.SECTOR_SIZE + C.PATCH_MARKER_OFFSET + 4],
            C.PATCH_MARKER,
        )

    def test_make_fdvdb_image_missing_loader(self):
        dst = os.path.join(self.tmp, "x.iso")
        with self.assertRaises(PathError):
            EsrService().make_fdvdb_image(
                self.src, dst, self.vt, self.v1, os.path.join(self.tmp, "nope.elf")
            )

    def test_make_fdvdb_image_uses_bundled_payloads_by_default(self):
        from edp.patcher.fdvdb import (
            VIDEO_TS_IFO_SIZE,
            VTS_01_0_IFO_SIZE,
            load_default_payloads,
        )

        video_ts_ifo, vts_01_0_ifo, loader = load_default_payloads()
        dst = os.path.join(self.tmp, "bundled.iso")
        report = EsrService().make_fdvdb_image(self.src, dst)  # sem caminhos

        self.assertEqual(report.video_ts_ifo_size, VIDEO_TS_IFO_SIZE)
        self.assertEqual(report.vts_01_0_ifo_size, VTS_01_0_IFO_SIZE)
        self.assertEqual(report.loader_size, len(loader))
        with open(dst, "rb") as fh:
            blob = fh.read()
        self.assertEqual(
            blob[VIDEO_TS_IFO_OFFSET:VIDEO_TS_IFO_OFFSET + VIDEO_TS_IFO_SIZE], video_ts_ifo
        )
        self.assertEqual(
            blob[VTS_01_0_IFO_OFFSET:VTS_01_0_IFO_OFFSET + VTS_01_0_IFO_SIZE], vts_01_0_ifo
        )
        self.assertEqual(blob[LOADER_OFFSET:LOADER_OFFSET + len(loader)], loader)


class PayloadOverrideTests(unittest.TestCase):
    def test_env_override_dir_takes_priority(self):
        from edp.patcher import fdvdb

        tmp = tempfile.mkdtemp(prefix="edp_payloads_")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        override = os.path.join(tmp, "payloads")
        os.makedirs(override)

        vt = bytes([0xAA]) * fdvdb.VIDEO_TS_IFO_SIZE
        v1 = bytes([0xBB]) * fdvdb.VTS_01_0_IFO_SIZE
        ld = b"\x7fELF" + bytes([0xCC]) * 64
        for name, data in (
            (fdvdb.PAYLOAD_VIDEO_TS_IFO, vt),
            (fdvdb.PAYLOAD_VTS_01_0_IFO, v1),
            (fdvdb.PAYLOAD_LOADER, ld),
        ):
            with open(os.path.join(override, name), "wb") as fh:
                fh.write(data)

        prev = os.environ.get(fdvdb.ENV_FDVDB_DIR)
        os.environ[fdvdb.ENV_FDVDB_DIR] = override
        self.addCleanup(self._restore_env, fdvdb.ENV_FDVDB_DIR, prev)

        got_vt, got_v1, got_ld, source = fdvdb.resolve_payloads()
        self.assertEqual(source, override)
        self.assertEqual((got_vt, got_v1, got_ld), (vt, v1, ld))

    @staticmethod
    def _restore_env(name, prev):
        if prev is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = prev


if __name__ == "__main__":
    unittest.main()
