#!/usr/bin/env python3
"""Lancador cross-platform da GUI do edp (somente stdlib, Python 3.9+).

Por que existe: a GUI precisa de um interpretador com **Tk >= 8.6**. A situacao
varia por sistema operacional:

- **macOS**: o Python do sistema (``/usr/bin/python3``) traz o Tk 8.5 da Apple,
  quebrado em versoes recentes -- a janela abre vazia.
- **Linux**: ``tkinter`` costuma vir num pacote separado (``python3-tk``).
- **Windows**: vem junto com o instalador do python.org.

Este lancador procura um Python valido (honrando ``EDP_PYTHON``), ajusta o
``PYTHONPATH`` para ``./src`` e abre ``python -m edp.gui``. Ele mesmo pode ser
executado por qualquer ``python3`` disponivel, pois usa apenas a stdlib.

Uso:
    python3 run-gui.py            # abre a GUI
    python3 run-gui.py --print    # so diagnostica (nao abre janela)
    EDP_PYTHON=/caminho/python3 python3 run-gui.py   # interpretador preferido

No macOS/Linux ha o atalho ``./run-gui.sh``; no Windows, ``run-gui.bat``.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

# Menor versao de Tk aceitavel (8.5 da Apple abre a janela vazia no macOS).
MIN_TK = (8, 6)

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.join(_HERE, "src")

# Probe: importar tkinter ja falha se o modulo nao existir; imprimimos a versao
# de Tk para decidir. Nao cria janela (nao precisa de display) -> serve headless.
_PROBE = "import tkinter, sys; sys.stdout.write(str(tkinter.TkVersion))"


def _fmt(version):
    """(8, 6) -> '8.6'."""
    return ".".join(str(part) for part in version)


def _exists(exe):
    """Existe como caminho ou esta no PATH?"""
    if os.path.isabs(exe) or os.sep in exe or (os.altsep and os.altsep in exe):
        return os.path.exists(exe)
    return shutil.which(exe) is not None


def _parse_tk(text):
    """Extrai a primeira versao 'X.Y[.Z]' de ``text`` como tupla de ints."""
    for token in text.split():
        parts = token.split(".")
        try:
            numbers = tuple(int(part) for part in parts)
        except ValueError:
            continue
        if numbers:
            return numbers
    return None


def _candidate_commands():
    """Interpretadores a testar, do mais preferido ao menos.

    Cada item e uma lista de argv (permite ``py -3.12`` no Windows). A ordem
    privilegia: ``EDP_PYTHON`` -> o proprio interpretador -> interpretadores
    com Tk garantido -> fallbacks genericos.
    """
    commands = []

    def add(command):
        if command and command not in commands:
            commands.append(command)

    env_python = os.environ.get("EDP_PYTHON")
    if env_python:
        add([env_python])

    # Se o lancador ja roda sob um Python com Tk valido, reutilize-o.
    add([sys.executable])

    if os.name == "nt":
        # O launcher "py" escolhe a maior 3.x instalada.
        py = shutil.which("py")
        if py:
            for tag in ("-3.13", "-3.12", "-3.11", "-3.10", "-3.9", "-3"):
                add([py, tag])
        for name in ("python3", "python"):
            found = shutil.which(name)
            if found:
                add([found])
        for ver in ("313", "312", "311", "310", "39"):
            found = shutil.which("python" + ver)
            if found:
                add([found])
        local = os.environ.get("LOCALAPPDATA")
        if local:
            for ver in ("313", "312", "311", "310", "39"):
                add([os.path.join(local, "Programs", "Python", "Python" + ver, "python.exe")])
        for ver in ("313", "312", "311", "310", "39"):
            add(["C:\\Python%s\\python.exe" % ver])
    else:
        if sys.platform == "darwin":
            for ver in ("3.13", "3.12", "3.11", "3.10", "3.9"):
                add(["/opt/homebrew/bin/python" + ver])
                add(["/usr/local/bin/python" + ver])
                add(["/Library/Frameworks/Python.framework/Versions/%s/bin/python3" % ver])
        for ver in ("3.13", "3.12", "3.11", "3.10", "3.9"):
            found = shutil.which("python" + ver)
            if found:
                add([found])
        for name in ("python3", "python"):
            found = shutil.which(name)
            if found:
                add([found])
        add(["/usr/bin/python3"])
        add(["/usr/local/bin/python3"])

    return commands


def _probe(command):
    """Testa um candidato. Retorna ``(versao_tk_ou_None, status)``."""
    if not _exists(command[0]):
        return None, "nao encontrado"
    try:
        proc = subprocess.run(
            command + ["-c", _PROBE],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=20,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return None, "falha ao executar (%s)" % exc.__class__.__name__
    if proc.returncode != 0:
        return None, "sem tkinter"
    version = _parse_tk(proc.stdout.strip())
    if version is None:
        return None, "versao de Tk ilegivel"
    if version < MIN_TK:
        return None, "Tk %s (< %s)" % (_fmt(version), _fmt(MIN_TK))
    return version, "Tk %s" % _fmt(version)


def _find():
    """Retorna ``(comando, versao_tk, tentativas)``; comando None se nao achar."""
    attempts = []
    for command in _candidate_commands():
        version, status = _probe(command)
        attempts.append((command, status))
        if version is not None:
            return command, version, attempts
    return None, None, attempts


def _hints():
    """Instrucoes de instalacao especificas do SO."""
    if os.name == "nt":
        return [
            "Windows: instale o Python 3.9+ do site oficial (ja inclui o Tk):",
            "    https://www.python.org/downloads/windows/",
            "No instalador, marque \"tcl/tk and IDLE\".",
            "Ou prefira um interpretador: set EDP_PYTHON=C:\\caminho\\python.exe",
        ]
    if sys.platform == "darwin":
        return [
            "macOS: o Python do sistema traz Tk 8.5 (janela vazia). Instale um com Tk >= 8.6:",
            "    brew install python-tk@3.12      # Homebrew (Tk 9.x atual)",
            "    # ou o instalador do python.org 3.12 (traz Tk 8.6)",
            "Ou prefira: EDP_PYTHON=/caminho/python3 ./run-gui.sh",
        ]
    return [
        "Linux: instale o tkinter (pacote separado na maioria das distros):",
        "    Debian/Ubuntu: sudo apt install python3-tk",
        "    Fedora:        sudo dnf install python3-tkinter",
        "    Arch:          sudo pacman -S tk",
        "Ou prefira: EDP_PYTHON=/caminho/python3 ./run-gui.sh",
    ]


def _diagnose(attempts, chosen, version):
    print("edp: lancador da GUI (run-gui.py)")
    print("edp: sistema: %s | python do lancador: %s" % (sys.platform, sys.executable))
    print("edp: candidatos avaliados:")
    for command, status in attempts:
        print("    %-58s %s" % (" ".join(command), status))
    if chosen is None:
        print("edp: NENHUM Python com Tk >= %s encontrado." % _fmt(MIN_TK))
        for line in _hints():
            print("    " + line)
        return 1
    print("edp: escolhido: %s (%s)" % (" ".join(chosen), _fmt(version)))
    print("edp: rodaria: PYTHONPATH=%s %s -m edp.gui" % (_SRC, " ".join(chosen)))
    return 0


def _run(command, env):
    """Substitui o processo (POSIX) ou executa como filho (fallback/Windows)."""
    if os.name != "nt":
        try:
            os.execvpe(command[0], command, env)
        except OSError:
            pass  # cai no subprocess abaixo
    try:
        return subprocess.call(command, env=env)
    except OSError as exc:
        sys.stderr.write("edp: falha ao iniciar %s: %s\n" % (command[0], exc))
        return 1


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    print_only = "--print" in argv
    if print_only:
        argv = [arg for arg in argv if arg != "--print"]

    command, version, attempts = _find()

    if print_only:
        return _diagnose(attempts, command, version)

    if command is None:
        sys.stderr.write(
            "edp: nenhum Python com Tk >= %s encontrado.\n\n" % _fmt(MIN_TK)
        )
        for line in _hints():
            sys.stderr.write("  " + line + "\n")
        return 1

    if not os.path.isdir(os.path.join(_SRC, "edp")):
        sys.stderr.write(
            "edp: nao encontrei o pacote em %s\n"
            "     rode este lancador da raiz do repositorio (onde esta 'src/').\n"
            % _SRC
        )
        return 1

    env = dict(os.environ)
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = _SRC + (os.pathsep + existing if existing else "")

    run_command = command + ["-m", "edp.gui"] + argv
    return _run(run_command, env)


if __name__ == "__main__":
    sys.exit(main())
