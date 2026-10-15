"""Testes de portabilidade (macOS/Linux/Windows) do core e da CLI.

Validam a LOGICA de forma deterministica e independente do SO hospedeiro:

- comparacao de caminho com semantica do Windows via ``ntpath``;
- derivacao do nome de saida a partir de caminhos Windows;
- progresso em stderr nao interativo (sem ``\\r``) e em terminal (com ``\\r``);
- escrita tolerante a code page restrita (cp1252/ascii), sem ``UnicodeEncodeError``;
- decodificacao do SYSTEM.CNF em latin-1 (independente de locale).
"""

import io
import ntpath
import os
import posixpath
import sys
import tempfile
import unittest
from unittest import mock

from edp import cli
from edp.domain.models import IsoAnalysis
from edp.domain.system_cnf import parse_system_cnf
from edp.patcher import service
from edp.paths import default_output_path


class _FakeStream:
    """Stream de texto com ``isatty`` controlavel."""

    def __init__(self, tty=False):
        self.tty = tty
        self.parts = []

    def isatty(self):
        return self.tty

    def write(self, text):
        self.parts.append(text)

    def flush(self):
        pass

    def getvalue(self):
        return "".join(self.parts)


class SameFileLogicTests(unittest.TestCase):
    """Cobre o fallback de ``_same_file`` (destino inexistente)."""

    def test_windows_key_is_case_and_separator_insensitive(self):
        a = service._path_key("C:\\iso\\jogo.iso", ntpath)
        b = service._path_key("c:/ISO/JOGO.ISO", ntpath)
        self.assertEqual(a, b)

    def test_windows_key_distinguishes_different_names(self):
        a = service._path_key("C:\\iso\\jogo.iso", ntpath)
        b = service._path_key("C:\\iso\\outro.iso", ntpath)
        self.assertNotEqual(a, b)

    def test_posix_key_is_case_sensitive(self):
        a = service._path_key("/jogo/jogo.iso", posixpath)
        b = service._path_key("/jogo/JOGO.ISO", posixpath)
        self.assertNotEqual(a, b)

    def test_fallback_when_samefile_unavailable(self):
        # Simula "destino nao existe": samefile levanta OSError e o fallback
        # precisa reconhecer o mesmo caminho grafado com './' como igual.
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "jogo.iso")
            open(src, "wb").close()
            same_via_dot = os.path.join(tmp, ".", "jogo.iso")
            other = os.path.join(tmp, "outro.iso")
            with mock.patch.object(service.os.path, "samefile", side_effect=OSError):
                self.assertTrue(service.EsrService._same_file(src, same_via_dot))
                self.assertFalse(service.EsrService._same_file(src, other))

    def test_existing_same_file_detected_by_inode(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "jogo.iso")
            open(src, "wb").close()
            self.assertTrue(service.EsrService._same_file(src, src))


class DefaultOutputPathTests(unittest.TestCase):
    def test_posix_path(self):
        self.assertEqual(
            default_output_path("/jogo/God of War.iso", "esr"),
            "/jogo/God of War_esr.iso",
        )

    def test_no_extension_defaults_to_iso(self):
        self.assertEqual(
            default_output_path("/jogo/game", "fdvdb"), "/jogo/game_fdvdb.iso"
        )

    def test_windows_backslash_path(self):
        self.assertEqual(
            default_output_path("C:\\iso\\jogo.iso", "esr"),
            "C:\\iso\\jogo_esr.iso",
        )

    def test_windows_forward_slash_path(self):
        self.assertEqual(
            default_output_path("C:/iso/jogo.iso", "esr"),
            "C:/iso/jogo_esr.iso",
        )

    def test_windows_dotted_directory_is_not_an_extension(self):
        # O ponto pertence ao diretorio, nao ao arquivo: nao pode virar extensao.
        self.assertEqual(
            default_output_path("C:\\my.dir\\jogo", "esr"),
            "C:\\my.dir\\jogo_esr.iso",
        )

    def test_bare_filename(self):
        self.assertEqual(default_output_path("jogo", "unpatched"), "jogo_unpatched.iso")


class ProgressTests(unittest.TestCase):
    def setUp(self):
        cli._last_pct["value"] = -1
        self._stderr = sys.stderr

    def tearDown(self):
        cli._last_pct["value"] = -1
        sys.stderr = self._stderr

    def test_non_tty_emits_periodic_lines(self):
        stream = _FakeStream(tty=False)
        sys.stderr = stream
        total = 1000
        for done in range(0, total + 1, 25):
            cli._print_progress(done, total)
        out = stream.getvalue()
        self.assertNotIn("\r", out)
        self.assertIn("  gravando:   0%\n", out)
        self.assertIn("  gravando:  50%\n", out)
        self.assertIn("  gravando: 100%\n", out)
        # uma linha por bucket de 10% => 11 linhas (0..100)
        self.assertEqual(out.count("gravando"), 11)

    def test_non_tty_prints_100_once_in_a_full_run(self):
        stream = _FakeStream(tty=False)
        sys.stderr = stream
        total = 1000
        for done in range(0, total + 1):
            cli._print_progress(done, total)
        self.assertEqual(stream.getvalue().count("100%"), 1)

    def test_tty_uses_carriage_return(self):
        stream = _FakeStream(tty=True)
        sys.stderr = stream
        cli._print_progress(0, 1000)
        cli._print_progress(500, 1000)
        cli._print_progress(1000, 1000)
        out = stream.getvalue()
        self.assertIn("\r", out)
        self.assertTrue(out.endswith("\n"))

    def test_total_zero_is_noop(self):
        stream = _FakeStream(tty=False)
        sys.stderr = stream
        cli._print_progress(0, 0)
        self.assertEqual(stream.getvalue(), "")


class ConsoleEncodingTests(unittest.TestCase):
    def test_write_safe_replaces_unencodable_on_cp1252(self):
        # 0x81 e' indefinido em cp1252 (console Windows) e derrubaria a CLI.
        buf = io.BytesIO()
        stream = io.TextIOWrapper(buf, encoding="cp1252")
        cli._write_safe(stream, "Volume: \x81")
        stream.flush()
        self.assertEqual(buf.getvalue(), b"Volume: ?")

    def test_write_safe_replaces_unencodable_on_ascii(self):
        buf = io.BytesIO()
        stream = io.TextIOWrapper(buf, encoding="ascii")
        cli._write_safe(stream, "n\u00e3o")
        stream.flush()
        self.assertEqual(buf.getvalue(), b"n?o")

    def test_write_safe_passthrough_on_utf8(self):
        buf = io.BytesIO()
        stream = io.TextIOWrapper(buf, encoding="utf-8")
        cli._write_safe(stream, "a\u00e7\u00e3o")
        stream.flush()
        self.assertEqual(buf.getvalue(), "a\u00e7\u00e3o".encode("utf-8"))

    def test_print_analysis_survives_latin1_volume_id(self):
        # Regressao do gap: Volume ID byte-a-byte (0x81) nao pode derrubar a CLI
        # num console cp1252.
        buf = io.BytesIO()
        stream = io.TextIOWrapper(buf, encoding="cp1252")
        analysis = IsoAnalysis(
            size=1234,
            is_udf=False,
            volume_id=b"JOGO\x81ISO".decode("latin-1"),
        )
        with mock.patch.object(cli.sys, "stdout", stream):
            cli._print_analysis(analysis)
        stream.flush()
        self.assertIn(b"Volume ID", buf.getvalue())


class LocaleIndependenceTests(unittest.TestCase):
    def test_system_cnf_bytes_are_decoded_as_latin1(self):
        # Decodificacao explicita (latin-1), nao depende do locale do SO.
        cnf = parse_system_cnf(b"NAME = caf\xe9\r\nBOOT2 = cdrom0:\\SLUS_203.12;1\r\n")
        self.assertEqual(cnf.entries["NAME"], "caf\u00e9")
        self.assertEqual(cnf.boot_executable, "SLUS_203.12")


if __name__ == "__main__":
    unittest.main()
