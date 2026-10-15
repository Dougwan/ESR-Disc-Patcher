#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# run-gui.sh - Lancador da GUI do edp para macOS e Linux.
#
# Ele apenas encontra UM Python para executar `run-gui.py` (que faz a deteccao
# de Tk >= 8.6, ajusta o PYTHONPATH para ./src e abre a GUI). Toda a logica
# cross-platform vive em `run-gui.py`; aqui so escolhemos qual interpretador
# roda o lancador. No Windows, use `run-gui.bat`.
#
# Por que existe (macOS): o Python do sistema (/usr/bin/python3) usa o Tk 8.5
# da Apple, quebrado em versoes recentes do macOS - a janela abre VAZIA. O
# `run-gui.py` escolhe automaticamente um interpretador com Tk >= 8.6.
#
# Uso:
#   ./run-gui.sh            # abre a GUI
#   ./run-gui.sh --print    # so mostra o diagnostico (nao abre janela)
#   EDP_PYTHON=/caminho/python3 ./run-gui.sh   # interpretador preferido
# ---------------------------------------------------------------------------
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Basta um Python qualquer (stdlib) para iniciar o lancador. A escolha do
# interpretador COM Tk e feita dentro de run-gui.py.
for py in "${EDP_PYTHON:-}" python3 python; do
  [ -n "$py" ] || continue
  if command -v "$py" >/dev/null 2>&1; then
    exec "$py" "$SCRIPT_DIR/run-gui.py" "$@"
  fi
done

echo "edp: nenhum interpretador Python encontrado para iniciar o lancador." >&2
echo "     Instale o Python 3.9+ e rode: python3 run-gui.py" >&2
exit 1
