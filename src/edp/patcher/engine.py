"""Engine de patch ESR sobre um ``RandomAccessDevice``."""

from typing import Optional

from ..domain import constants as C
from ..domain.errors import AlreadyPatchedError, IsoStructureError, NotPatchedError, NotUdfError
from ..domain.models import PatchReport
from ..iso.udf import find_volume_recognition, looks_patched
from .descriptor import patch_directory_descriptor
from .dvd_data import load_dvd_video_data


class EsrPatchEngine:
    """Aplica/remove o patch ESR; o dispositivo pode ser arquivo ou memoria."""

    def __init__(self, device, dvd_data: Optional[bytes] = None):
        self._device = device
        self._dvd_data = dvd_data if dvd_data is not None else load_dvd_video_data()

    # -- consultas -----------------------------------------------------------
    def is_patched(self) -> bool:
        return looks_patched(self._device)

    def validate_layout(self) -> None:
        if self._device.size() < C.MIN_IMAGE_SIZE:
            raise IsoStructureError(
                "imagem menor que o minimo exigido (%d bytes)" % C.MIN_IMAGE_SIZE
            )
        if find_volume_recognition(self._device) is None:
            raise NotUdfError("Volume Recognition Sequence UDF nao encontrada")

    # -- operacoes -----------------------------------------------------------
    def patch(self, image_path: Optional[str] = None) -> PatchReport:
        self.validate_layout()
        if self.is_patched():
            raise AlreadyPatchedError("imagem ja possui o patch ESR")

        written = 0
        # 1) backup dos descritores originais
        originals = {}
        for target, backup in C.TARGET_DESCRIPTORS:
            block = self._device.read_at(target * C.SECTOR_SIZE, C.SECTOR_SIZE)
            originals[target] = block
            self._device.write_at(backup * C.SECTOR_SIZE, block)
            written += C.SECTOR_SIZE

        # 2) reescrita dos descritores
        for target, _backup in C.TARGET_DESCRIPTORS:
            patched = patch_directory_descriptor(originals[target], C.DVD_VIDEO_LBA)
            self._device.write_at(target * C.SECTOR_SIZE, patched)
            written += C.SECTOR_SIZE

        # 3) estrutura DVD-Video sintetica
        self._device.write_at(C.DVD_VIDEO_LBA * C.SECTOR_SIZE, self._dvd_data)
        written += len(self._dvd_data)

        self._device.flush()
        return PatchReport(
            action="patch",
            image_path=image_path,
            targets=tuple(t for t, _ in C.TARGET_DESCRIPTORS),
            dvd_video_lba=C.DVD_VIDEO_LBA,
            bytes_written=written,
            image_size=self._device.size(),
        )

    def unpatch(self, image_path: Optional[str] = None) -> PatchReport:
        self.validate_layout()
        if not self.is_patched():
            raise NotPatchedError("imagem nao possui o patch ESR")

        written = 0
        zeros = bytes(C.SECTOR_SIZE)
        for target, backup in C.TARGET_DESCRIPTORS:
            original = self._device.read_at(backup * C.SECTOR_SIZE, C.SECTOR_SIZE)
            self._device.write_at(target * C.SECTOR_SIZE, original)
            self._device.write_at(backup * C.SECTOR_SIZE, zeros)
            written += 2 * C.SECTOR_SIZE

        self._device.write_at(C.DVD_VIDEO_LBA * C.SECTOR_SIZE, bytes(C.DVD_VIDEO_SIZE))
        written += C.DVD_VIDEO_SIZE

        self._device.flush()
        return PatchReport(
            action="unpatch",
            image_path=image_path,
            targets=tuple(t for t, _ in C.TARGET_DESCRIPTORS),
            dvd_video_lba=C.DVD_VIDEO_LBA,
            bytes_written=written,
            image_size=self._device.size(),
        )
