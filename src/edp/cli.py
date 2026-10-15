"""Interface de linha de comando do edp."""

import argparse
import sys
from typing import Optional

from . import __version__
from .domain.errors import EsrError
from .domain.models import IsoAnalysis
from .patcher.service import EsrService
from .paths import default_output_path

_last_pct = {"value": -1}
_PROGRESS_STEP = 10  # em modo nao interativo, uma linha a cada 10%


def _is_tty(stream) -> bool:
    """``True`` se ``stream`` e' um terminal interativo (sem levantar excecao)."""
    try:
        return bool(stream.isatty())
    except (AttributeError, ValueError, OSError):
        return False


def _write_safe(stream, text: str) -> None:
    """Escreve ``text`` tolerando code pages restritas (ex.: console Windows).

    Em terminais/pipes UTF-8 nada muda. Se a codificacao do stream nao
    representar algum caractere (ex.: cp1252 com ``U+0081``, comum em Volume ID
    decodificada em latin-1), reescreve com substituicao para nunca abortar a
    CLI com ``UnicodeEncodeError``.
    """
    try:
        stream.write(text)
    except UnicodeEncodeError:
        encoding = getattr(stream, "encoding", None) or "ascii"
        stream.write(text.encode(encoding, "replace").decode(encoding))


def _emit(text: str) -> None:
    """Imprime uma linha em stdout de forma segura para a code page do console."""
    _write_safe(sys.stdout, text + "\n")


def _print_progress(done: int, total: int) -> None:
    if total <= 0:
        return
    pct = int(done * 100 / total)
    stream = sys.stderr

    if _is_tty(stream):
        # Terminal: redesenha a linha com carriage return (comportamento atual).
        # evita spam: so redesenha quando o percentual inteiro muda
        if pct == _last_pct["value"] and done < total:
            return
        _last_pct["value"] = pct
        stream.write("\r  gravando: %3d%%" % pct)
        stream.flush()
        if done >= total:
            stream.write("\n")
            _last_pct["value"] = -1
        return

    # Saida nao interativa (pipe, arquivo de log ou cmd.exe legado): o '\r' nao
    # ajuda, entao emitimos linhas periodicas a cada 10%.
    bucket = 100 if pct >= 100 else (pct // _PROGRESS_STEP) * _PROGRESS_STEP
    if bucket > _last_pct["value"]:
        _last_pct["value"] = bucket
        stream.write("  gravando: %3d%%\n" % bucket)
        stream.flush()
    if done >= total:
        _last_pct["value"] = -1


def _print_analysis(analysis: IsoAnalysis) -> None:
    _emit("Imagem:            %d bytes (%.1f MiB)" % (analysis.size, analysis.size / 1048576))
    _emit("UDF:               %s" % ("sim (%s @ setor %d)" % (analysis.udf.standard, analysis.udf.sector) if analysis.is_udf else "nao"))
    _emit("Estado do patch:   %s" % analysis.patch_state)
    _emit("Volume ID:         %s" % (analysis.volume_id or "-"))
    _emit("Game ID:           %s" % (analysis.game_id or "-"))
    _emit("Regiao:            %s" % (analysis.region or "-"))
    _emit("Boot executable:   %s" % (analysis.boot_executable or "-"))
    if analysis.elf is not None:
        _emit("ELF:               32-bit=%s, LE=%s, MIPS=%s, entry=0x%X"
              % (analysis.elf.is_32bit, analysis.elf.is_little_endian,
                 analysis.elf.is_mips, analysis.elf.entry))
    for problem in analysis.elf_problems:
        _emit("  ! ELF: %s" % problem)
    for warning in analysis.warnings:
        _emit("  ! %s" % warning)


def _cmd_info(args) -> int:
    _print_analysis(EsrService().analyze(args.image))
    return 0


def _cmd_patch(args) -> int:
    service = EsrService()
    if args.in_place:
        report = service.patch_in_place(args.image, progress=_print_progress)
    else:
        dst = args.output or default_output_path(args.image, "esr")
        report = service.patch_to_new_file(
            args.image, dst, progress=_print_progress, overwrite=args.overwrite
        )
    _emit("Patch aplicado em %s (%d bytes gravados)." % (report.image_path, report.bytes_written))
    return 0


def _cmd_fdvdb(args) -> int:
    dst = args.output or default_output_path(args.image, "fdvdb")
    report = EsrService().make_fdvdb_image(
        args.image,
        dst,
        args.video_ts_ifo,
        args.vts_01_0_ifo,
        args.loader,
        progress=_print_progress,
        overwrite=args.overwrite,
    )
    _emit(
        "Disco FreeDVDBoot+ESR gerado em %s (origem dos payloads: %s; "
        "VIDEO_TS.IFO=%d, VTS_01_0.IFO=%d, loader=%d bytes)."
        % (report.image_path, report.payload_source,
           report.video_ts_ifo_size, report.vts_01_0_ifo_size, report.loader_size)
    )
    return 0


def _cmd_unpatch(args) -> int:
    service = EsrService()
    if args.in_place:
        report = service.unpatch_in_place(args.image, progress=_print_progress)
    else:
        dst = args.output or default_output_path(args.image, "unpatched")
        report = service.unpatch_to_new_file(
            args.image, dst, progress=_print_progress, overwrite=args.overwrite
        )
    _emit("Patch removido em %s (%d bytes gravados)." % (report.image_path, report.bytes_written))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="edp",
        description="Aplica/remove o patch ESR em imagens de disco de PlayStation 2.",
    )
    parser.add_argument("--version", action="version", version="edp %s" % __version__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_info = sub.add_parser("info", help="Inspeciona uma imagem sem altera-la.")
    p_info.add_argument("image")
    p_info.set_defaults(func=_cmd_info)

    p_patch = sub.add_parser("patch", help="Aplica o patch ESR.")
    p_patch.add_argument("image")
    p_patch.add_argument("-o", "--output", help="Imagem de saida (padrao: <nome>_esr.iso).")
    p_patch.add_argument("--in-place", action="store_true", help="Patcha a propria imagem (destrutivo).")
    p_patch.add_argument("--overwrite", action="store_true", help="Sobrescreve a saida se existir.")
    p_patch.set_defaults(func=_cmd_patch)

    p_fdvdb = sub.add_parser(
        "fdvdb",
        help="Gera disco ESR + FreeDVDBoot (boot direto, sem instalar nada no PS2).",
        epilog=(
            "Payloads: por padrao os embutidos no pacote. Para usar outros "
            "(ex.: firmware Phat 2.10/2.12/3.04), coloque os 3 arquivos "
            "(payload_VIDEO_TS.IFO, payload_VTS_01_0.IFO, esr.elf) numa pasta "
            "'payloads/' ao lado do projeto ou aponte EDP_FDVDB_DIR. "
            "As flags --video-ts-ifo/--vts-01-0-ifo/--loader tem prioridade."
        ),
    )
    p_fdvdb.add_argument("image")
    p_fdvdb.add_argument("-o", "--output", help="Imagem de saida (padrao: <nome>_fdvdb.iso).")
    p_fdvdb.add_argument(
        "--video-ts-ifo", help="Override do payload VIDEO_TS.IFO (padrao: embutido)."
    )
    p_fdvdb.add_argument(
        "--vts-01-0-ifo", help="Override do payload VTS_01_0.IFO (padrao: embutido)."
    )
    p_fdvdb.add_argument(
        "--loader", help="Override do loader ESR (.elf) (padrao: embutido)."
    )
    p_fdvdb.add_argument("--overwrite", action="store_true", help="Sobrescreve a saida se existir.")
    p_fdvdb.set_defaults(func=_cmd_fdvdb)

    p_unpatch = sub.add_parser("unpatch", help="Remove o patch ESR.")
    p_unpatch.add_argument("image")
    p_unpatch.add_argument("-o", "--output", help="Imagem de saida (padrao: <nome>_unpatched.iso).")
    p_unpatch.add_argument("--in-place", action="store_true", help="Remove o patch da propria imagem.")
    p_unpatch.add_argument("--overwrite", action="store_true", help="Sobrescreve a saida se existir.")
    p_unpatch.set_defaults(func=_cmd_unpatch)

    return parser


def main(argv: Optional[list] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except EsrError as exc:
        _write_safe(sys.stderr, "erro: %s\n" % exc)
        return 2
    except OSError as exc:  # rede de seguranca: E/S inesperada nao deve virar traceback
        _write_safe(sys.stderr, "erro de E/S: %s\n" % exc)
        return 2
    except KeyboardInterrupt:  # pragma: no cover
        _write_safe(sys.stderr, "\ninterrompido\n")
        return 130


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
