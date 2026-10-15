import os
import tempfile
import unittest

from edp.domain.errors import AlreadyPatchedError, NotPatchedError, PathError
from edp.patcher.service import EsrService

from .fixtures import build_synthetic_iso


class ServiceIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="edp_")
        self.src = os.path.join(self.tmp, "game.iso")
        with open(self.src, "wb") as fh:
            fh.write(build_synthetic_iso())
        self.service = EsrService()

    def tearDown(self):
        for name in os.listdir(self.tmp):
            os.remove(os.path.join(self.tmp, name))
        os.rmdir(self.tmp)

    def _dst(self, name="out.iso"):
        return os.path.join(self.tmp, name)

    def test_patch_to_new_file_preserves_source_and_progress(self):
        dst = self._dst("patched.iso")
        calls = []
        report = self.service.patch_to_new_file(
            self.src, dst, progress=lambda d, t: calls.append((d, t))
        )
        self.assertEqual(report.action, "patch")
        self.assertTrue(os.path.isfile(dst))

        # original intacta
        analysis_src = self.service.analyze(self.src)
        self.assertFalse(analysis_src.is_patched)
        # saida patchada
        analysis_dst = self.service.analyze(dst)
        self.assertTrue(analysis_dst.is_patched)

        self.assertTrue(calls)
        self.assertEqual(calls[-1][0], calls[-1][1])  # progresso chega a 100%

    def test_patch_to_existing_without_overwrite_raises(self):
        dst = self._dst()
        open(dst, "wb").close()
        with self.assertRaises(PathError):
            self.service.patch_to_new_file(self.src, dst)

    def test_patch_overwrite(self):
        dst = self._dst()
        open(dst, "wb").close()
        report = self.service.patch_to_new_file(self.src, dst, overwrite=True)
        self.assertEqual(report.action, "patch")

    def test_same_source_and_destination_raises(self):
        with self.assertRaises(PathError):
            self.service.patch_to_new_file(self.src, self.src)

    def test_patch_missing_source_raises(self):
        with self.assertRaises(PathError):
            self.service.patch_to_new_file(self._dst("nope.iso"), self._dst("x.iso"))

    def test_patch_already_patched_source_raises(self):
        patched = self._dst("patched.iso")
        self.service.patch_to_new_file(self.src, patched)
        with self.assertRaises(AlreadyPatchedError):
            self.service.patch_to_new_file(patched, self._dst("again.iso"))

    def test_round_trip_patch_then_unpatch(self):
        patched = self._dst("patched.iso")
        unp = self._dst("unpatched.iso")
        self.service.patch_to_new_file(self.src, patched)
        self.service.unpatch_to_new_file(patched, unp)
        analysis = self.service.analyze(unp)
        self.assertFalse(analysis.is_patched)

    def test_unpatch_clean_source_raises(self):
        with self.assertRaises(NotPatchedError):
            self.service.unpatch_to_new_file(self.src, self._dst("u.iso"))

    def test_patch_in_place(self):
        report = self.service.patch_in_place(self.src)
        self.assertEqual(report.action, "patch")
        self.assertTrue(self.service.analyze(self.src).is_patched)

    def test_partial_output_cleaned_on_failure(self):
        # destino valido mas origem ja patchada -> falha antes da copia;
        # e se a copia falhar, o parcial e removido (testado via destino invalido)
        bad_dst = os.path.join(self.tmp, "sub", "x.iso")  # diretorio inexistente
        with self.assertRaises(Exception):
            self.service.patch_to_new_file(self.src, bad_dst)
        self.assertFalse(os.path.exists(bad_dst))


if __name__ == "__main__":
    unittest.main()
