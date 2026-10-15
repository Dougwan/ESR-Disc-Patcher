"""Overlay FreeDVDBoot sobre um disco ESR-patchado (auto-boot, sem instalar).

Combina o ESR patch (que faz o disco parecer DVD-Video) com o exploit do DVD
player (FreeDVDBoot), para que um disco gravado boote direto num PS2 sem
modchip e sem nada instalado (somente firmware suportado + console em English).

A rotina replica o `Patcher.cpp` (edo9300) + as notas de byte do CTurt:

    VIDEO_TS.BUP -> VTS_01_0.IFO            (renomeia o File Identifier)
    f0 07 00 00 0a 00 -> 00 38 00 00 0a 00   (VIDEO_TS.IFO: tam 2032 -> 14336)
    f0 07 00 00 0b 00 -> 00 30 00 00 11 00   (VTS_01_0.IFO: tam 12288, LBA 145)
    0x45000: VIDEO_TS.IFO exploit (14336 bytes)
    0x48800: VTS_01_0.IFO        (12288 bytes)
    0x4B800: loader ELF do ESR
"""

import functools
import hashlib
import os
from dataclasses import dataclass
from typing import Optional, Tuple

from ..domain.errors import FdvdbError

# Offsets absolutos (setor * 2048)
VIDEO_TS_IFO_OFFSET = 0x45000   # LBA 138
VTS_01_0_IFO_OFFSET = 0x48800   # LBA 145
LOADER_OFFSET = 0x4B800         # LBA 151
SCAN_LIMIT = VIDEO_TS_IFO_OFFSET  # varre so a area UDF, nao os payloads

VIDEO_TS_IFO_SIZE = 14336       # 0x3800 (7 setores)
VTS_01_0_IFO_SIZE = 12288       # 0x3000 (6 setores)

_NAME_OLD = b"VIDEO_TS.BUP"
_NAME_NEW = b"VTS_01_0.IFO"     # mesmo comprimento (12 bytes)

_AD_VIDEO_TS_IFO = bytes.fromhex("f00700000a00")
_AD_VIDEO_TS_IFO_NEW = bytes.fromhex("003800000a00")
_AD_VTS_01_IFO = bytes.fromhex("f00700000b00")
_AD_VTS_01_IFO_NEW = bytes.fromhex("003000001100")

# -- payloads embutidos (assets/fdvdb) --------------------------------------
_ASSETS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "fdvdb"
)
PAYLOAD_VIDEO_TS_IFO = "payload_VIDEO_TS.IFO"
PAYLOAD_VTS_01_0_IFO = "payload_VTS_01_0.IFO"
PAYLOAD_LOADER = "esr.elf"

# SHA-256 de integridade dos payloads embutidos (pacote "FDVDB_ESR_Patcher").
_VIDEO_TS_IFO_SHA256 = "e4a41769d71989ca40b4c64a79cf8c5b6b695cb1779af71cd2978f00329f37d6"
_VTS_01_0_IFO_SHA256 = "c26206e1e4f4405855495037eb725a9be0bb964d2d163fd712edd30e626fd3c0"
_LOADER_SHA256 = "dccbaaee464ced9bbd62f25db7c4e02b549be6f4e7705fddb5ff970ba1403fa4"


def asset_path(name: str) -> str:
    return os.path.join(_ASSETS_DIR, name)


def _load_asset(name: str, expected_size: int, expected_sha256: str) -> bytes:
    path = asset_path(name)
    if not os.path.isfile(path):
        raise FdvdbError("asset ausente: %s" % path)
    with open(path, "rb") as fh:
        data = fh.read()
    if len(data) != expected_size:
        raise FdvdbError(
            "tamanho inesperado de %s: %d (esperado %d)" % (name, len(data), expected_size)
        )
    digest = hashlib.sha256(data).hexdigest()
    if digest != expected_sha256:
        raise FdvdbError("SHA-256 de %s nao confere: %s" % (name, digest))
    return data


@functools.lru_cache(maxsize=1)
def load_default_payloads() -> Tuple[bytes, bytes, bytes]:
    """Retorna (VIDEO_TS.IFO, VTS_01_0.IFO, loader) validados do pacote."""
    return (
        _load_asset(PAYLOAD_VIDEO_TS_IFO, VIDEO_TS_IFO_SIZE, _VIDEO_TS_IFO_SHA256),
        _load_asset(PAYLOAD_VTS_01_0_IFO, VTS_01_0_IFO_SIZE, _VTS_01_0_IFO_SHA256),
        _load_asset(PAYLOAD_LOADER, 14921, _LOADER_SHA256),
    )


# -- override opcional (ex.: payloads de firmware Phat) ---------------------
# Prioridade: 1) EDP_FDVDB_DIR  2) ./payloads  3) embutidos no pacote.
# O diretorio de override deve conter os 3 arquivos com os mesmos nomes.
ENV_FDVDB_DIR = "EDP_FDVDB_DIR"
_PAYLOAD_FILES = (PAYLOAD_VIDEO_TS_IFO, PAYLOAD_VTS_01_0_IFO, PAYLOAD_LOADER)


def override_dir() -> Optional[str]:
    """Diretorio de override valido (com os 3 arquivos), ou None."""
    candidates = []
    env = os.environ.get(ENV_FDVDB_DIR)
    if env:
        candidates.append(env)
    candidates.append(os.path.join(os.getcwd(), "payloads"))
    for directory in candidates:
        if all(os.path.isfile(os.path.join(directory, name)) for name in _PAYLOAD_FILES):
            return directory
    return None


def _read(path: str) -> bytes:
    if not os.path.isfile(path):
        raise FdvdbError("arquivo nao encontrado: %s" % path)
    with open(path, "rb") as fh:
        return fh.read()


def resolve_payloads() -> Tuple[bytes, bytes, bytes, str]:
    """Retorna (VIDEO_TS.IFO, VTS_01_0.IFO, loader, origem).

    A origem e o diretorio de override usado ou a string ``"embutidos"``.
    Os payloads de override NAO passam por SHA-256 (podem ser outros firmwares);
    o tamanho e validado no overlay.
    """
    directory = override_dir()
    if directory is None:
        video_ts_ifo, vts_01_0_ifo, loader = load_default_payloads()
        return video_ts_ifo, vts_01_0_ifo, loader, "embutidos"
    return (
        _read(os.path.join(directory, PAYLOAD_VIDEO_TS_IFO)),
        _read(os.path.join(directory, PAYLOAD_VTS_01_0_IFO)),
        _read(os.path.join(directory, PAYLOAD_LOADER)),
        directory,
    )


@dataclass(frozen=True)
class FdvdbReport:
    image_path: Optional[str]
    video_ts_ifo_size: int
    vts_01_0_ifo_size: int
    loader_size: int
    name_renames: int
    ad_rewrites: int
    bytes_written: int
    payload_source: str = "embutidos"


def _replace_all(buf: bytearray, old: bytes, new: bytes, label: str) -> int:
    if len(old) != len(new):
        raise FdvdbError("padrao de tamanho diferente para '%s'" % label)
    count = 0
    start = 0
    while True:
        idx = buf.find(old, start)
        if idx < 0:
            break
        buf[idx:idx + len(new)] = new
        count += 1
        start = idx + len(new)
    if count == 0:
        raise FdvdbError(
            "padrao '%s' (%s) nao encontrado: a imagem nao parece ESR-patchada"
            % (label, old.hex(" "))
        )
    return count


def apply_fdvdb_overlay(
    device,
    video_ts_ifo: bytes,
    vts_01_0_ifo: bytes,
    loader: bytes,
    image_path: Optional[str] = None,
    payload_source: str = "embutidos",
) -> FdvdbReport:
    """Aplica o overlay FreeDVDBoot; exige um disco ja ESR-patchado."""
    if len(video_ts_ifo) != VIDEO_TS_IFO_SIZE:
        raise FdvdbError(
            "VIDEO_TS.IFO deve ter %d bytes (tem %d)"
            % (VIDEO_TS_IFO_SIZE, len(video_ts_ifo))
        )
    if len(vts_01_0_ifo) != VTS_01_0_IFO_SIZE:
        raise FdvdbError(
            "VTS_01_0.IFO deve ter %d bytes (tem %d)"
            % (VTS_01_0_IFO_SIZE, len(vts_01_0_ifo))
        )
    if not loader:
        raise FdvdbError("loader ELF vazio")

    size = device.size()
    end = max(VIDEO_TS_IFO_OFFSET + len(video_ts_ifo),
              VTS_01_0_IFO_OFFSET + len(vts_01_0_ifo),
              LOADER_OFFSET + len(loader))
    if end > size:
        raise FdvdbError("imagem pequena demais para receber o overlay")

    region = bytearray(device.read_at(0, min(SCAN_LIMIT, size)))
    renames = _replace_all(region, _NAME_OLD, _NAME_NEW, "rename BUP")
    ads = _replace_all(region, _AD_VIDEO_TS_IFO, _AD_VIDEO_TS_IFO_NEW, "VIDEO_TS.IFO short_ad")
    ads += _replace_all(region, _AD_VTS_01_IFO, _AD_VTS_01_IFO_NEW, "VTS_01_0.IFO short_ad")

    written = len(region) + len(video_ts_ifo) + len(vts_01_0_ifo) + len(loader)
    device.write_at(0, bytes(region))
    device.write_at(VIDEO_TS_IFO_OFFSET, video_ts_ifo)
    device.write_at(VTS_01_0_IFO_OFFSET, vts_01_0_ifo)
    device.write_at(LOADER_OFFSET, loader)
    device.flush()

    return FdvdbReport(
        image_path=image_path,
        video_ts_ifo_size=len(video_ts_ifo),
        vts_01_0_ifo_size=len(vts_01_0_ifo),
        loader_size=len(loader),
        name_renames=renames,
        ad_rewrites=ads,
        bytes_written=written,
        payload_source=payload_source,
    )
