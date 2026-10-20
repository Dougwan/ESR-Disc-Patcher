"""Testes de ponta a ponta da CLI (build_parser + main + dispatch)."""

import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

from edp import cli
from edp.patcher.service import EsrService

from .fixtures import build_synthetic_iso

_VIDEO_TS_IFO = bytes([0x0A]) * 14336
_VTS_01_0_IFO = bytes([0x0B]) * 12288
_LOADER = b"\x7fELF" + bytes([0x5C]) * 4096


def _run(argv):
    """Executa ``cli.main`` capturando stdout/stderr; devolve (rc, out, err)."""
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = cli.main(argv)
    return rc, out.getvalue(), err.getvalue()


class CliTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="edp_cli_")
        self.src = os.path.join(self.tmp, "game.iso")
        with open(self.src, "wb") as fh:
            fh.write(build_synthetic_iso())
        cli._last_pct["value"] = -1

    def tearDown(self):
        for name in os.listdir(self.tmp):
            os.remove(os.path.join(self.tmp, name))
        os.rmdir(self.tmp)
        cli._last_pct["value"] = -1

    def _dst(self, name="out.iso"):
        return os.path.join(self.tmp, name)


class BuildParserTests(CliTestCase):
    """Cobre o parser isoladamente: subcomandos, flags e defaults."""

    def test_requires_a_subcommand(self):
        parser = cli.build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args([])

    def test_patch_defaults(self):
        parser = cli.build_parser()
        args = parser.parse_args(["patch", "jogo.iso"])
        self.assertEqual(args.image, "jogo.iso")
        self.assertIsNone(args.output)
        self.assertFalse(args.in_place)
        self.assertFalse(args.overwrite)
        self.assertIs(args.func, cli._cmd_patch)

    def test_patch_flags(self):
        parser = cli.build_parser()
        args = parser.parse_args(
            ["patch", "jogo.iso", "-o", "saida.iso", "--in-place", "--overwrite"]
        )
        self.assertEqual(args.output, "saida.iso")
        self.assertTrue(args.in_place)
        self.assertTrue(args.overwrite)

    def test_fdvdb_payload_overrides(self):
        parser = cli.build_parser()
        args = parser.parse_args(
            ["fdvdb", "jogo.iso", "--video-ts-ifo", "a.ifo",
             "--vts-01-0-ifo", "b.ifo", "--loader", "c.elf"]
        )
        self.assertEqual(args.video_ts_ifo, "a.ifo")
        self.assertEqual(args.vts_01_0_ifo, "b.ifo")
        self.assertEqual(args.loader, "c.elf")
        self.assertIs(args.func, cli._cmd_fdvdb)

    def test_unpatch_defaults(self):
        parser = cli.build_parser()
        args = parser.parse_args(["unpatch", "jogo.iso"])
        self.assertIs(args.func, cli._cmd_unpatch)

    def test_unknown_command_exits_nonzero(self):
        parser = cli.build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["nope", "jogo.iso"])

    def test_version_flag_exits_zero(self):
        parser = cli.build_parser()
        with redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as ctx:
                parser.parse_args(["--version"])
        self.assertEqual(ctx.exception.code, 0)


class MainInfoTests(CliTestCase):
    def test_info_prints_analysis_and_returns_zero(self):
        rc, out, err = _run(["info", self.src])
        self.assertEqual(rc, 0)
        self.assertEqual(err, "")
        self.assertIn("Game ID:", out)
        self.assertIn("SLUS_203.12", out)
        self.assertIn("Estado do patch:   clean", out)

    def test_info_missing_file_returns_nonzero_without_traceback(self):
        rc, out, err = _run(["info", self._dst("nope.iso")])
        self.assertEqual(rc, 2)
        self.assertIn("erro:", err)
        self.assertEqual(out, "")


class MainPatchTests(CliTestCase):
    def test_patch_to_new_file_default_output_name(self):
        rc, out, err = _run(["patch", self.src])
        self.assertEqual(rc, 0)
        expected_dst = self._dst("game_esr.iso")
        self.assertTrue(os.path.isfile(expected_dst))
        self.assertIn(expected_dst, out)
        analysis = EsrService().analyze(expected_dst)
        self.assertTrue(analysis.is_patched)
        # origem permanece intacta
        self.assertFalse(EsrService().analyze(self.src).is_patched)

    def test_patch_explicit_output(self):
        dst = self._dst("custom.iso")
        rc, _, _ = _run(["patch", self.src, "-o", dst])
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.isfile(dst))

    def test_patch_without_overwrite_fails_cleanly(self):
        dst = self._dst("existe.iso")
        open(dst, "wb").close()
        rc, out, err = _run(["patch", self.src, "-o", dst])
        self.assertEqual(rc, 2)
        self.assertIn("erro:", err)
        self.assertEqual(out, "")

    def test_patch_overwrite_flag_allows_it(self):
        dst = self._dst("existe.iso")
        open(dst, "wb").close()
        rc, _, _ = _run(["patch", self.src, "-o", dst, "--overwrite"])
        self.assertEqual(rc, 0)

    def test_patch_already_patched_source_returns_nonzero(self):
        patched = self._dst("p.iso")
        _run(["patch", self.src, "-o", patched])
        rc, out, err = _run(["patch", patched, "-o", self._dst("p2.iso")])
        self.assertEqual(rc, 2)
        self.assertIn("erro:", err)

    def test_patch_in_place(self):
        rc, out, _ = _run(["patch", self.src, "--in-place"])
        self.assertEqual(rc, 0)
        self.assertIn(self.src, out)
        self.assertTrue(EsrService().analyze(self.src).is_patched)


class MainUnpatchTests(CliTestCase):
    def test_round_trip_via_cli(self):
        patched = self._dst("p.iso")
        unp = self._dst("u.iso")
        rc_p, _, _ = _run(["patch", self.src, "-o", patched])
        rc_u, out, _ = _run(["unpatch", patched, "-o", unp])
        self.assertEqual((rc_p, rc_u), (0, 0))
        self.assertFalse(EsrService().analyze(unp).is_patched)
        self.assertIn(unp, out)

    def test_unpatch_clean_source_returns_nonzero(self):
        rc, _, err = _run(["unpatch", self.src])
        self.assertEqual(rc, 2)
        self.assertIn("erro:", err)


class MainFdvdbTests(CliTestCase):
    def setUp(self):
        super().setUp()
        self.vt = self._dst("VIDEO_TS.IFO")
        self.v1 = self._dst("VTS_01_0.IFO")
        self.ld = self._dst("loader.elf")
        for path, data in ((self.vt, _VIDEO_TS_IFO), (self.v1, _VTS_01_0_IFO), (self.ld, _LOADER)):
            with open(path, "wb") as fh:
                fh.write(data)

    def test_fdvdb_with_explicit_payloads(self):
        dst = self._dst("game_fdvdb.iso")
        rc, out, err = _run(
            ["fdvdb", self.src, "-o", dst,
             "--video-ts-ifo", self.vt, "--vts-01-0-ifo", self.v1, "--loader", self.ld]
        )
        self.assertEqual(rc, 0, err)
        self.assertTrue(os.path.isfile(dst))
        self.assertIn("FreeDVDBoot+ESR", out)
        self.assertIn("flags", out)  # payload_source reportado

    def test_fdvdb_missing_loader_returns_nonzero(self):
        rc, out, err = _run(
            ["fdvdb", self.src, "--loader", self._dst("nope.elf"),
             "--video-ts-ifo", self.vt, "--vts-01-0-ifo", self.v1]
        )
        self.assertEqual(rc, 2)
        self.assertIn("erro:", err)


if __name__ == "__main__":
    unittest.main()
