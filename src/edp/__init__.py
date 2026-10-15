"""edp — toolkit para aplicar/remover o patch ESR em imagens de PS2.

Arquitetura em camadas (dependencia sempre para baixo):

    domain   -> puro, sem I/O
    iso      -> leitura de dispositivo + UDF + ISO9660
    patcher  -> engine de patch + blob DVD-Video
    service  -> casos de uso (analisar, patch por copia, in-place)
    cli/gui  -> apresentacao
"""

from .domain.models import IsoAnalysis, PatchReport  # noqa: F401
from .patcher.service import EsrService  # noqa: F401

__all__ = ["EsrService", "IsoAnalysis", "PatchReport"]
__version__ = "0.1.0"
