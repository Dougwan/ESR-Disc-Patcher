"""Parser do SYSTEM.CNF (arquivo de boot do disco de PS2).

Formato tipico::

    BOOT2 = cdrom0:\\SLUS_203.12;1
    VER = 1.00
    VMODE = NTSC
"""

from typing import Dict

from .models import SystemCnf

_COMMENT_MARKER = "//"


def _strip_comment(line: str) -> str:
    idx = line.find(_COMMENT_MARKER)
    return line[:idx] if idx != -1 else line


def parse_system_cnf(text: str) -> SystemCnf:
    """Interpreta o texto do SYSTEM.CNF em um objeto ``SystemCnf``."""
    if isinstance(text, bytes):
        text = text.decode("latin-1")

    entries: Dict[str, str] = {}
    for raw_line in text.splitlines():
        line = _strip_comment(raw_line).strip()
        if not line or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip().upper()
        if not key:
            continue
        entries[key] = value.strip()

    return SystemCnf(entries=entries, boot2=entries.get("BOOT2"))
