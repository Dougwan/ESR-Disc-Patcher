"""Inspecao best-effort de uma imagem: UDF, ISO9660, SYSTEM.CNF e ELF."""

from ..domain import constants as C
from ..domain.elf import parse_elf_header, validate_ps2_elf
from ..domain.errors import EsrError
from ..domain.gameid import game_id_from_boot, region_for
from ..domain.models import IsoAnalysis
from ..domain.system_cnf import parse_system_cnf
from .iso9660 import Iso9660Volume
from .udf import find_volume_recognition, looks_patched

_ELF_PROBE_BYTES = 64


class IsoInspector:
    """Produz um ``IsoAnalysis`` sem alterar a imagem."""

    def __init__(self, device):
        self._device = device

    def analyze(self) -> IsoAnalysis:
        device = self._device
        warnings = []
        size = device.size()

        udf = find_volume_recognition(device)
        if udf is None:
            warnings.append("Volume Recognition Sequence UDF nao encontrada.")
        is_patched = looks_patched(device)

        volume = None
        if size >= C.VRS_START_SECTOR * C.SECTOR_SIZE:
            volume = Iso9660Volume.open(device)
        if volume is None:
            warnings.append("Primary Volume Descriptor ISO9660 nao encontrado.")

        system_cnf = None
        boot_executable = None
        elf = None
        elf_problems = []
        game_id = None
        region = None
        volume_id = volume.volume_id if volume else None

        if volume is not None:
            entry = volume.find("SYSTEM.CNF")
            if entry is None or entry.is_dir:
                warnings.append("SYSTEM.CNF nao encontrado na raiz.")
            else:
                try:
                    text = volume.read_file(entry)
                    system_cnf = parse_system_cnf(text)
                    boot_executable = system_cnf.boot_executable
                except EsrError as exc:  # pragma: no cover - defensivo
                    warnings.append("Falha ao ler SYSTEM.CNF: %s" % exc)

        if boot_executable:
            game_id = game_id_from_boot(boot_executable)
            region = region_for(game_id)
            if volume is not None:
                elf_entry = volume.find(game_id) or volume.find(boot_executable)
                if elf_entry is None or elf_entry.is_dir:
                    warnings.append(
                        "ELF de boot '%s' nao encontrado na raiz." % boot_executable
                    )
                else:
                    try:
                        prefix = volume.read_prefix(elf_entry, _ELF_PROBE_BYTES)
                        elf = parse_elf_header(prefix)
                        elf_problems = validate_ps2_elf(elf)
                    except EsrError as exc:
                        # best-effort: imagem truncada ou ELF invalido nao deve
                        # abortar a analise (o diagnostico continua com aviso).
                        elf_problems.append(str(exc))

        return IsoAnalysis(
            size=size,
            is_udf=udf is not None,
            udf=udf,
            is_patched=is_patched,
            volume_id=volume_id,
            system_cnf=system_cnf,
            boot_executable=boot_executable,
            elf=elf,
            elf_problems=elf_problems,
            game_id=game_id,
            region=region,
            warnings=warnings,
        )
