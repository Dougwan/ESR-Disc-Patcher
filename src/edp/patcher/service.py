"""Casos de uso de alto nivel: analisar, patch/unpatch por copia ou in-place."""

import os
from typing import Callable, Optional

from ..domain.errors import AlreadyPatchedError, NotPatchedError, NotUdfError, PathError
from ..domain.models import IsoAnalysis, PatchReport
from ..iso.device import FileDevice
from ..iso.inspector import IsoInspector
from .engine import EsrPatchEngine
from .fdvdb import FdvdbReport, apply_fdvdb_overlay, resolve_payloads

ProgressFn = Callable[[int, int], None]
_COPY_BUFFER = 1024 * 1024


def _path_key(path: str, pathmod=os.path) -> str:
    """Chave de caminho para comparacao portavel.

    ``normcase`` dobra caixa e separador no Windows (identidade em POSIX);
    ``abspath`` ja aplica ``normpath``. ``pathmod`` e injetavel para permitir
    validar a semantica do Windows (``ntpath``) rodando em outro SO.
    """
    return pathmod.normcase(pathmod.normpath(pathmod.abspath(path)))


class EsrService:
    """Orquestra copia + patch mantendo a imagem original intacta por padrao."""

    # -- leitura -------------------------------------------------------------
    @staticmethod
    def analyze(path: str) -> IsoAnalysis:
        if not os.path.isfile(path):
            raise PathError("arquivo de entrada inexistente: %s" % path)
        try:
            with FileDevice(path, "rb") as device:
                return IsoInspector(device).analyze()
        except OSError as exc:
            raise PathError("falha ao abrir '%s': %s" % (path, exc))

    # -- patch ---------------------------------------------------------------
    def patch_to_new_file(
        self,
        src: str,
        dst: str,
        progress: Optional[ProgressFn] = None,
        overwrite: bool = False,
    ) -> PatchReport:
        return self._copy_then(
            self._precheck_for_patch, src, dst, overwrite, progress,
            lambda device, out: EsrPatchEngine(device).patch(image_path=out),
        )

    def patch_in_place(self, path: str, progress: Optional[ProgressFn] = None) -> PatchReport:
        self._precheck_for_patch(path, path, overwrite=True, in_place=True)
        try:
            with FileDevice(path, "r+b") as device:
                report = EsrPatchEngine(device).patch(image_path=path)
        except OSError as exc:
            raise PathError("falha de E/S em '%s': %s" % (path, exc))
        if progress:
            progress(report.image_size, report.image_size)
        return report

    def make_fdvdb_image(
        self,
        src: str,
        dst: str,
        video_ts_ifo_path: Optional[str] = None,
        vts_01_0_ifo_path: Optional[str] = None,
        loader_path: Optional[str] = None,
        progress: Optional[ProgressFn] = None,
        overwrite: bool = False,
    ) -> FdvdbReport:
        """Gera um disco ESR + FreeDVDBoot (boot direto, sem instalar nada).

        Fluxo: valida -> copia -> ESR patch -> overlay FreeDVDBoot.
        Os payloads/loader vem: (1) dos caminhos explicitos, (2) de um diretorio
        de override (``EDP_FDVDB_DIR`` ou ``./payloads``) ou (3) embutidos
        no pacote (``assets/fdvdb``).

        Ver ADR-0005 (docs/adr/0005-overlay-freedvdboot.md) para o porque desta
        feature existir ao lado do patch ESR descrito na ADR-0002.
        """
        video_ts_ifo, vts_01_0_ifo, loader, source = self._resolve_payloads(
            video_ts_ifo_path, vts_01_0_ifo_path, loader_path
        )

        def _apply(device, out: str) -> FdvdbReport:
            EsrPatchEngine(device).patch(image_path=out)
            return apply_fdvdb_overlay(
                device, video_ts_ifo, vts_01_0_ifo, loader,
                image_path=out, payload_source=source,
            )

        return self._copy_then(self._precheck_for_patch, src, dst, overwrite, progress, _apply)

    # -- unpatch -------------------------------------------------------------
    def unpatch_to_new_file(
        self,
        src: str,
        dst: str,
        progress: Optional[ProgressFn] = None,
        overwrite: bool = False,
    ) -> PatchReport:
        return self._copy_then(
            self._precheck_for_unpatch, src, dst, overwrite, progress,
            lambda device, out: EsrPatchEngine(device).unpatch(image_path=out),
        )

    def unpatch_in_place(self, path: str, progress: Optional[ProgressFn] = None) -> PatchReport:
        self._precheck_for_unpatch(path, path, overwrite=True, in_place=True)
        try:
            with FileDevice(path, "r+b") as device:
                report = EsrPatchEngine(device).unpatch(image_path=path)
        except OSError as exc:
            raise PathError("falha de E/S em '%s': %s" % (path, exc))
        if progress:
            progress(report.image_size, report.image_size)
        return report

    # -- internos ------------------------------------------------------------
    def _copy_then(
        self,
        precheck_fn: Callable[[str, str, bool], IsoAnalysis],
        src: str,
        dst: str,
        overwrite: bool,
        progress: Optional[ProgressFn],
        apply_fn: Callable[[FileDevice, str], object],
    ):
        """Copia ``src`` -> ``dst`` e aplica ``apply_fn`` sobre o destino.

        Agrupa o shape comum a ``patch_to_new_file``, ``unpatch_to_new_file``
        e ``make_fdvdb_image``: precheck -> copia -> abre o destino -> aplica
        -> limpa o destino parcial em caso de erro. ``apply_fn`` recebe o
        ``FileDevice`` aberto e o caminho do destino, e retorna o relatorio
        (``PatchReport`` ou ``FdvdbReport``).
        """
        precheck_fn(src, dst, overwrite)
        try:
            self._copy_with_progress(src, dst, progress)
            with FileDevice(dst, "r+b") as device:
                return apply_fn(device, dst)
        except OSError as exc:
            self._safe_unlink(dst)
            raise PathError("falha de E/S na saida '%s': %s" % (dst, exc))
        except Exception:
            self._safe_unlink(dst)
            raise

    @staticmethod
    def _resolve_payloads(
        video_ts_ifo_path: Optional[str],
        vts_01_0_ifo_path: Optional[str],
        loader_path: Optional[str],
    ) -> tuple:
        """Resolve os 3 payloads (base = override/embutido, flags tem prioridade)."""
        video_ts_ifo, vts_01_0_ifo, loader, source = resolve_payloads()
        if video_ts_ifo_path or vts_01_0_ifo_path or loader_path:
            source = "flags"
            if video_ts_ifo_path:
                video_ts_ifo = EsrService._read_file(video_ts_ifo_path)
            if vts_01_0_ifo_path:
                vts_01_0_ifo = EsrService._read_file(vts_01_0_ifo_path)
            if loader_path:
                loader = EsrService._read_file(loader_path)
        return video_ts_ifo, vts_01_0_ifo, loader, source

    @staticmethod
    def _validate_paths(src: str, dst: str, overwrite: bool, in_place: bool) -> None:
        if not os.path.isfile(src):
            raise PathError("arquivo de entrada inexistente: %s" % src)
        if in_place:
            return
        if EsrService._same_file(src, dst):
            raise PathError("origem e destino sao o mesmo arquivo")
        if os.path.exists(dst) and not overwrite:
            raise PathError("arquivo de saida ja existe: %s" % dst)

    @staticmethod
    def _same_file(src: str, dst: str) -> bool:
        """True se origem e destino apontam para o mesmo arquivo.

        Usa ``samefile`` (inode) quando o destino existe, o que cobre sistemas
        de arquivos case-insensitive (ex.: APFS/NTFS), onde duas grafias
        diferentes resolvem para o mesmo arquivo. Quando o destino ainda nao
        existe, cai para comparacao de chave de caminho normalizada
        (``normcase``/``normpath``/``abspath``), que no Windows tambem ignora
        maiusculas/minusculas e uniformiza o separador.
        """
        try:
            return os.path.samefile(src, dst)
        except OSError:
            return _path_key(src) == _path_key(dst)

    def _precheck_for_patch(
        self, src: str, dst: str, overwrite: bool, in_place: bool = False
    ) -> IsoAnalysis:
        self._validate_paths(src, dst, overwrite, in_place)
        analysis = self.analyze(src)
        if not analysis.is_udf:
            raise NotUdfError("a imagem nao contem a Volume Recognition Sequence UDF")
        if analysis.is_patched:
            raise AlreadyPatchedError("a imagem ja possui o patch ESR")
        return analysis

    def _precheck_for_unpatch(
        self, src: str, dst: str, overwrite: bool, in_place: bool = False
    ) -> IsoAnalysis:
        self._validate_paths(src, dst, overwrite, in_place)
        analysis = self.analyze(src)
        if not analysis.is_patched:
            raise NotPatchedError("a imagem nao possui o patch ESR")
        return analysis

    @staticmethod
    def _copy_with_progress(src: str, dst: str, progress: Optional[ProgressFn]) -> None:
        try:
            total = os.path.getsize(src)
            done = 0
            if progress:
                progress(0, total)
            with open(src, "rb") as fin, open(dst, "wb") as fout:
                while True:
                    chunk = fin.read(_COPY_BUFFER)
                    if not chunk:
                        break
                    fout.write(chunk)
                    done += len(chunk)
                    if progress:
                        progress(done, total)
        except OSError as exc:
            raise PathError("falha ao copiar para '%s': %s" % (dst, exc))

    @staticmethod
    def _read_file(path: str) -> bytes:
        if not os.path.isfile(path):
            raise PathError("arquivo nao encontrado: %s" % path)
        with open(path, "rb") as fh:
            return fh.read()

    @staticmethod
    def _safe_unlink(path: str) -> None:
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError:  # pragma: no cover - limpeza best-effort
            pass
