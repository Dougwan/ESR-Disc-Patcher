# Portabilidade (macOS · Linux · Windows)

O `edp` é **um único código-fonte** (Python 3.9+, **somente biblioteca padrão**)
que roda nos três sistemas operacionais. **Não há binário por plataforma nem
empacotador** (PyInstaller etc.) — ver
[`adr/0004-sem-dependencias-de-runtime.md`](adr/0004-sem-dependencias-de-runtime.md).
A CLI (`edp`) é agnóstica de SO; apenas a **GUI** exige `tkinter` com **Tk ≥ 8.6**.

## Matriz de requisitos

| SO | Python 3.9+ | `tkinter` / Tk ≥ 8.6 |
|----|-------------|----------------------|
| **macOS** | `brew install python@3.12` ou python.org | python.org traz Tk 8.6; Homebrew: `brew install python-tk@3.12`. O Python do **sistema** traz **Tk 8.5** (quebrado: janela vazia) |
| **Linux** | `python3` do sistema | pacote separado: `apt install python3-tk` · `dnf install python3-tkinter` · `pacman -S tk` |
| **Windows** | python.org (marque *tcl/tk and IDLE*) | vem no instalador oficial do python.org |

## Lançadores

A detecção de Tk vive em **`run-gui.py`** (stdlib, roda sob qualquer `python3`):
ele testa os candidatos (`EDP_PYTHON` → interpretador atual → caminhos por SO),
escolhe o primeiro com **Tk ≥ 8.6**, ajusta `PYTHONPATH` para `./src` e abre
`python -m edp.gui`. Os atalhos por SO apenas o invocam:

| SO | Atalho | Observação |
|----|--------|-----------|
| macOS / Linux | `./run-gui.sh` | encontra um `python3` e delega a `run-gui.py` |
| Windows | `run-gui.bat` | usa `py -3` ou `python` e delega a `run-gui.py` |
| qualquer | `python3 run-gui.py` | forma direta, sem atalho |

- `--print` só diagnostica (lista candidatos, versão de Tk e por que cada um foi
  aceito/recusado) — **não abre janela**.
- `EDP_PYTHON=/caminho/python3` define o interpretador **preferido**.
- Se nenhum candidato servir, a mensagem de erro é **específica do SO**:
  - Linux → `apt/dnf/pacman install ...` do `python3-tk`;
  - Windows → baixar do python.org (marcar tcl/tk);
  - macOS → `brew install python-tk@3.12` ou python.org.

## Instalação via `pip` (entry points)

`python3 -m pip install .` (ou `-e .`) cria os comandos cross-platform:

- `edp` → `edp.cli:main`
- `edp-gui` → `edp.gui.app:main`

O `package-data` (`pyproject.toml`) embute todos os assets, inclusive o `.ico`:
`assets/*.bin`, `assets/fdvdb/*`, `assets/icons/*`.

## Ícone por SO

Implementado em `src/edp/gui/app.py` (`EdpApp._apply_icon`), tolerante a falha
(ícone é cosmético; asset ausente não impede a GUI de abrir):

- **Windows:** `edp.ico` via `iconbitmap` (formato nativo da barra de
  tarefas/Explorer);
- **macOS / Linux:** `edp_128.png` via `iconphoto`;
- no **macOS**, o ícone do **Dock/Finder** vem do bundle `EDP.app/` — ver abaixo.

## `EDP.app` — conveniência **somente macOS**

O bundle `EDP.app/` **não é portátil nem autônomo**: executa um Python embutido
(`Contents/MacOS/EDP`, cópia de um Homebrew) e depende de `<repo>/src`; precisa
ficar na raiz do repositório e não é assinado. É apenas conveniência para abrir a
GUI no macOS (Dock/Finder). Linux/Windows usam `run-gui.py` / `run-gui.bat`.

## O que é (e não é) verificado

- Verificado em **macOS** (esta máquina): lançadores, fallback do Tk 8.5 → 9.1,
  ícone, GUI headless smoke.
- **Não** verificado de fato em Windows/Linux (sem acesso a essas máquinas nesta
  tarefa): a lógica dos ramos por SO é exercitada por simulação, mas o
  comportamento real de `iconbitmap`, `py -3` e dos caminhos de instalação do
  Windows é **risco residual** até um teste real.
