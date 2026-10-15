"""Modelos de dominio (dataclasses imutaveis)."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class UdfInfo:
    """Resultado da deteccao da Volume Recognition Sequence UDF."""

    standard: str          # "NSR02" ou "NSR03"
    sector: int            # setor onde o descritor NSR foi encontrado


@dataclass(frozen=True)
class ElfHeader:
    """Subconjunto relevante do cabecalho ELF."""

    elf_class: int         # 1 = 32-bit, 2 = 64-bit
    data_encoding: int     # 1 = little-endian, 2 = big-endian
    machine: int           # e_machine (8 = MIPS)
    entry: int
    phoff: int
    phnum: int
    shoff: int
    shnum: int

    @property
    def is_32bit(self) -> bool:
        return self.elf_class == 1

    @property
    def is_little_endian(self) -> bool:
        return self.data_encoding == 1

    @property
    def is_mips(self) -> bool:
        return self.machine == 8


@dataclass(frozen=True)
class SystemCnf:
    """Conteudo interpretado do SYSTEM.CNF."""

    entries: dict            # chave (UPPER) -> valor original
    boot2: Optional[str] = None   # valor cru de BOOT2

    @property
    def boot_executable(self) -> Optional[str]:
        """Nome normalizado do ELF de boot (ex.: 'SLUS_203.12')."""
        raw = self.boot2 or self.entries.get("BOOT")
        if not raw:
            return None
        value = raw.strip()
        # remove prefixo de dispositivo (cdrom0:\ ou cdrom0:/)
        lowered = value.lower()
        for prefix in ("cdrom0:\\", "cdrom0:/", "cdrom0:"):
            if lowered.startswith(prefix):
                value = value[len(prefix):]
                break
        # remove extensao de versao ISO  ;1
        if ";" in value:
            value = value.split(";", 1)[0]
        value = value.replace("\\", "/").strip("/")
        return value.upper() if value else None


@dataclass(frozen=True)
class IsoAnalysis:
    """Diagnostico completo e best-effort de uma imagem."""

    size: int
    is_udf: bool
    udf: Optional[UdfInfo] = None
    is_patched: bool = False
    volume_id: Optional[str] = None
    system_cnf: Optional[SystemCnf] = None
    boot_executable: Optional[str] = None
    elf: Optional[ElfHeader] = None
    elf_problems: List[str] = field(default_factory=list)
    game_id: Optional[str] = None
    region: Optional[str] = None
    warnings: List[str] = field(default_factory=list)

    @property
    def patch_state(self) -> str:
        if not self.is_udf:
            return "not_udf"
        return "patched" if self.is_patched else "clean"


@dataclass(frozen=True)
class PatchReport:
    """Resultado de uma operacao de patch/unpatch."""

    action: str                              # "patch" | "unpatch"
    image_path: Optional[str]
    targets: tuple                           # LBAs de descritores alterados
    dvd_video_lba: int
    bytes_written: int
    image_size: int
