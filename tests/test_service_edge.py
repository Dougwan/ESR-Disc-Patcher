"""Testes de borda dos casos de uso (limpeza de saida, erros tipados)."""

import os
import shutil
import tempfile
import unittest

from edp.domain.errors import AlreadyPatchedError, PathError
from edp.iso.iso9660 import _parse_dir_record
from edp.patcher.service import EsrService

from .fixtures import build_synthetic_iso


class ServiceEdgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="edp_edge_")
        self.src = os.path.join(self.tmp, "game.iso")
        with open(self.src, "wb") as fh:
            fh.write(build_synthetic_iso())
        self.service = EsrService()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_analyze_missing_path_raises_patherror(self):
        with self.assertRaises(PathError):
            self.service.analyze(os.path.join(self.tmp, "nope.iso"))

    def test_missing_output_dir_raises_patherror(self):
        # diretorio de saida inexistente: deve virar PathError, nao OSError cru
        dst = os.path.join(self.tmp, "sub", "out.iso")
        with self.assertRaises(PathError):
            self.service.patch_to_new_file(self.src, dst)

    def test_output_is_directory_raises_patherror(self):
        dst = os.path.join(self.tmp, "out.iso")
        os.mkdir(dst)
        with self.assertRaises(PathError):
            self.service.patch_to_new_file(self.src, dst, overwrite=True)
        self.assertTrue(os.path.isdir(dst))

    def test_failed_copy_leaves_no_partial_output(self):
        # progresso que falha no meio da copia: o parcial precisa ser removido
        dst = os.path.join(self.tmp, "partial.iso")
        calls = []

        def boom(done, total):
            calls.append(done)
            if len(calls) >= 2:
                raise RuntimeError("falha simulada no progresso")

        with self.assertRaises(RuntimeError):
            self.service.patch_to_new_file(self.src, dst, progress=boom)
        self.assertFalse(os.path.exists(dst))

    def test_unpatch_in_place_round_trip(self):
        self.service.patch_in_place(self.src)
        self.assertTrue(self.service.analyze(self.src).is_patched)
        self.service.unpatch_in_place(self.src)
        self.assertFalse(self.service.analyze(self.src).is_patched)

    def test_hardlink_to_source_rejected_as_same_file(self):
        # destino e um hardlink da origem (mesmo inode): deve ser recusado para
        # nao truncar a origem durante a copia, mesmo com overwrite=True
        dst = os.path.join(self.tmp, "link.iso")
        os.link(self.src, dst)
        with self.assertRaises(PathError):
            self.service.patch_to_new_file(self.src, dst, overwrite=True)
        # a origem continua intacta
        self.assertEqual(os.path.getsize(self.src), len(build_synthetic_iso()))

    def test_fdvdb_source_already_patched_raises(self):
        patched = os.path.join(self.tmp, "patched.iso")
        self.service.patch_to_new_file(self.src, patched)
        with self.assertRaises(AlreadyPatchedError):
            self.service.make_fdvdb_image(patched, os.path.join(self.tmp, "x.iso"))

    def test_parser_ignores_truncated_dir_record(self):
        # length = 34 no primeiro byte, mas o registro so tem 6 bytes
        self.assertIsNone(_parse_dir_record(b"\x22" + b"\x00" * 5))
        self.assertIsNone(_parse_dir_record(b"\x02" + b"\x00" * 5))


if __name__ == "__main__":
    unittest.main()
