"""Engine de patch ESR: descritores UDF, blob DVD-Video e casos de uso."""

from .engine import EsrPatchEngine  # noqa: F401
from .fdvdb import FdvdbReport, apply_fdvdb_overlay  # noqa: F401
from .service import EsrService  # noqa: F401
