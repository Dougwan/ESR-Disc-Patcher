"""Parser minimo de ISO9660 (PVD + diretorio raiz) para inspecao.

Nao pretende ser um parser ISO completo: apenas o suficiente para localizar e
ler arquivos na raiz (ex.: ``SYSTEM.CNF`` e o ELF de boot).
"""

from dataclasses import dataclass
from typing import List, Optional

from ..domain import constants as C


@dataclass(frozen=True)
class DirEntry:
    name: str
    lba: int
    size: int
    is_dir: bool


def _first_sector_with(device, predicate, start, count):
    total = device.size()
    for sector in range(start, start + count):
        offset = sector * C.SECTOR_SIZE
        if offset + C.SECTOR_SIZE > total:
            return None
        block = device.read_at(offset, C.SECTOR_SIZE)
        if predicate(block):
            return block
    return None


def read_pvd(device) -> Optional[bytes]:
    """Retorna o bloco do Primary Volume Descriptor, se existir."""
    def is_pvd(block: bytes) -> bool:
        return block[0] == C.PVD_TYPE and block[1:6] == C.ISO9660_MAGIC

    return _first_sector_with(
        device, is_pvd, C.VRS_START_SECTOR, C.ISO9660_SCAN_SECTORS
    )


def _parse_dir_record(rec: bytes) -> Optional[DirEntry]:
    length = rec[0]
    if length < C.DIR_RECORD_MIN_LENGTH or len(rec) < length:
        return None
    lba = int.from_bytes(rec[2:6], "little")
    size = int.from_bytes(rec[10:14], "little")
    flags = rec[25]
    name_len = rec[32]
    raw_name = rec[33:33 + name_len]
    if name_len == 1 and raw_name in (b"\x00", b"\x01"):
        name = "." if raw_name == b"\x00" else ".."
    else:
        text = raw_name.decode("latin-1").rstrip("\x00")
        if ";" in text:
            text = text.split(";", 1)[0]
        name = text
    return DirEntry(name=name, lba=lba, size=size, is_dir=bool(flags & 0x02))


class Iso9660Volume:
    """Acesso de alto nivel a raiz de um volume ISO9660."""

    def __init__(self, device, pvd: bytes):
        self._device = device
        self._pvd = pvd
        self.volume_id = (
            pvd[C.PVD_VOLUME_ID_OFFSET:
                C.PVD_VOLUME_ID_OFFSET + C.PVD_VOLUME_ID_LENGTH]
            .decode("latin-1")
            .strip(" \x00")
        )
        self._root = _parse_dir_record(pvd[C.PVD_ROOT_RECORD_OFFSET:
                                           C.PVD_ROOT_RECORD_OFFSET + C.DIR_RECORD_MIN_LENGTH])

    @classmethod
    def open(cls, device) -> Optional["Iso9660Volume"]:
        pvd = read_pvd(device)
        if pvd is None:
            return None
        return cls(device, pvd)

    def list_dir(self, entry: DirEntry) -> List[DirEntry]:
        """Lista os registros de um diretorio."""
        result: List[DirEntry] = []
        if not entry.is_dir:
            return result
        total_sectors = (entry.size + C.SECTOR_SIZE - 1) // C.SECTOR_SIZE
        for i in range(total_sectors):
            offset = (entry.lba + i) * C.SECTOR_SIZE
            if offset + C.SECTOR_SIZE > self._device.size():
                break
            sector = self._device.read_at(offset, C.SECTOR_SIZE)
            pos = 0
            while pos < C.SECTOR_SIZE:
                rec_len = sector[pos]
                if rec_len == 0:
                    break
                parsed = _parse_dir_record(sector[pos:pos + rec_len])
                if parsed is not None:
                    result.append(parsed)
                pos += rec_len
        return result

    def list_root(self) -> List[DirEntry]:
        return self.list_dir(self._root)

    def find(self, name: str) -> Optional[DirEntry]:
        """Localiza um arquivo pelo nome (case-insensitive, sem ';1')."""
        target = name.upper()
        for entry in self.list_root():
            if entry.name.upper() == target:
                return entry
        return None

    def read_prefix(self, entry: DirEntry, length: int) -> bytes:
        """Le apenas os primeiros ``length`` bytes de um arquivo."""
        n = min(length, entry.size)
        if n <= 0:
            return b""
        return self._device.read_at(entry.lba * C.SECTOR_SIZE, n)

    def read_file(self, entry: DirEntry) -> bytes:
        remaining = entry.size
        chunks = []
        offset = entry.lba * C.SECTOR_SIZE
        while remaining > 0:
            chunk = min(remaining, C.SECTOR_SIZE)
            chunks.append(self._device.read_at(offset, chunk))
            offset += chunk
            remaining -= chunk
        return b"".join(chunks)
