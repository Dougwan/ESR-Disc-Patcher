"""Carregamento do blob DVD-Video embutido (12 setores / 24576 bytes).

O blob e o dado binario que faz o disco ser aceito como DVD-Video pelo
mechacon. Ele e versionado no repositorio (asset), nao gerado em tempo de
execucao, e verificado por SHA-256 para garantir integridade.
"""

import functools
import hashlib
import os

from ..domain import constants as C
from ..domain.errors import DvdDataError

DVD_DATA_SHA256 = "d61083e8bc90a959c21958e46216a8531c2095c2f6f780b779d9489f3fd5a845"
_ASSET_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets",
    "dvd_video_data.bin",
)


@functools.lru_cache(maxsize=1)
def load_dvd_video_data() -> bytes:
    """Retorna o blob DVD-Video validado (tamanho + SHA-256)."""
    if not os.path.isfile(_ASSET_PATH):
        raise DvdDataError("asset ausente: %s" % _ASSET_PATH)
    with open(_ASSET_PATH, "rb") as fh:
        data = fh.read()
    if len(data) != C.DVD_VIDEO_SIZE:
        raise DvdDataError(
            "tamanho inesperado do asset: %d (esperado %d)"
            % (len(data), C.DVD_VIDEO_SIZE)
        )
    digest = hashlib.sha256(data).hexdigest()
    if digest != DVD_DATA_SHA256:
        raise DvdDataError("SHA-256 do asset nao confere: %s" % digest)
    return data
