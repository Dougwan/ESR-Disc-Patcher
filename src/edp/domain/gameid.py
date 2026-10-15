"""Identificacao best-effort de game id e regiao a partir do ELF de boot."""

from typing import Optional

_REGION_BY_PREFIX = {
    "SCUS": "NTSC-U",
    "SLUS": "NTSC-U",
    "SCES": "PAL",
    "SLES": "PAL",
    "SCED": "PAL",
    "SLED": "PAL",
    "SCPS": "NTSC-J",
    "SLPS": "NTSC-J",
    "SLPM": "NTSC-J",
    "SCPM": "NTSC-J",
    "SCAJ": "NTSC-J",
    "SLAJ": "NTSC-J",
    "SCKA": "NTSC-K",
    "SLKA": "NTSC-K",
}


def game_id_from_boot(boot_executable: Optional[str]) -> Optional[str]:
    """Extrai o game id do nome do ELF de boot (ex.: 'SLUS_203.12')."""
    if not boot_executable:
        return None
    name = boot_executable.replace("\\", "/").split("/")[-1].strip()
    return name or None


def region_for(game_id: Optional[str]) -> Optional[str]:
    """Mapeia o prefixo do game id para uma regiao de video."""
    if not game_id or len(game_id) < 4:
        return None
    return _REGION_BY_PREFIX.get(game_id[:4].upper())
