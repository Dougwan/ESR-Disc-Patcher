"""Deteccao de UDF e do estado de patch ESR numa imagem."""

from typing import Optional

from ..domain import constants as C
from ..domain.models import UdfInfo


def find_volume_recognition(device) -> Optional[UdfInfo]:
    """Procura a Volume Recognition Sequence (ECMA-167) da UDF.

    Um descritor NSR tem byte 0 == 0x00 (structure type) e os bytes 1..4 com a
    identificacao ``NSR02``/``NSR03``. A VRS comeca no setor 16.
    """
    total = device.size()
    last = C.VRS_START_SECTOR + C.VRS_SCAN_SECTORS
    sector = C.VRS_START_SECTOR
    while sector < last:
        offset = sector * C.SECTOR_SIZE
        if offset + C.SECTOR_SIZE > total:
            break
        block = device.read_at(offset, 6)
        if block[0] == 0x00 and block[1:6] in C.VRS_NSR_IDS:
            return UdfInfo(standard=block[1:6].decode("ascii"), sector=sector)
        sector += 1
    return None


def looks_patched(device) -> bool:
    """Indica se o marcador ``+NSR`` esta presente na copia de backup."""
    offset = C.PATCH_MARKER_LBA * C.SECTOR_SIZE + C.PATCH_MARKER_OFFSET
    if offset + len(C.PATCH_MARKER) > device.size():
        return False
    return device.read_at(offset, len(C.PATCH_MARKER)) == C.PATCH_MARKER
