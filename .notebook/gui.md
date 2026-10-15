# Notebook — GUI e empacotamento (edp)

Notas operacionais reutilizáveis sobre a camada de apresentação e o bundle.
Escopo: `src/edp/gui/**`, `run-gui.sh`, `EDP.app/**`, `pyproject.toml`, `README.md`.

## Regra de ouro

- A GUI é **só apresentação**: coleta entrada, chama `EsrService` e mostra
  resultado/progresso. **Zero lógica de patch** (não importa `domain`/`patcher`
  internals além de `EsrService`, `IsoAnalysis`, `EsrError`).
- Contrato estável do core usado pela GUI: `analyze`, `make_fdvdb_image`,
  `patch_to_new_file`, `patch_in_place`, `unpatch_*` + `IsoAnalysis`,
  `FdvdbReport`, `EsrError`.

## Modelo de concorrência

- Trabalho roda em `threading.Thread(daemon=True)`; resultados/progresso vão
  para uma `queue.Queue`; a thread principal drena via `self.after(80ms,
  _poll_queue)`. **Nunca** tocar em widgets fora da thread principal.
- `_set_busy(True)` desabilita **toda** a entrada (entry + botões + patch). Isso
  evita uma segunda análise concorrente disparada por Enter/botões.
- `_poll_queue` reagenda em `finally` e isola cada `_handle_message` em
  try/except: um erro no handler não pode congelar a UI em "ocupado".
- Fechar a janela durante o trabalho pede confirmação (`WM_DELETE_WINDOW`), pois
  a cópia é O(tamanho) e a saída ficaria parcial.

## Portabilidade (macOS · Linux · Windows)

- **Modo (a)**: fonte roda nos 3 SOs com Python 3.9+ (com Tk). **Sem** binário
  standalone / PyInstaller; **sem** dependências novas. Só a GUI exige Tk.
- **Lançadores** (lógica única em `run-gui.py`, stdlib; roda sob qualquer
  `python3`):
  - `run-gui.py` — testa candidatos (`EDP_PYTHON` → `sys.executable` → caminhos
    por SO), escolhe o 1º com **Tk ≥ 8.6**, exporta `PYTHONPATH=<repo>/src` e
    abre `-m edp.gui` (POSIX via `os.execvpe`; Windows via `subprocess`).
    `--print` só diagnostica; erro é **específico do SO**.
  - `run-gui.sh` (macOS/Linux) — acha um `python3` e delega a `run-gui.py`.
  - `run-gui.bat` (Windows, CRLF) — usa `py -3`/`python` e delega.
- **Tk por SO**: macOS sistema = Tk 8.5 (quebrado → janela vazia); Linux =
  pacote `python3-tk`; Windows = vem no instalador python.org.
- **Ícone por SO** (`app.py:_apply_icon`): Windows usa `edp.ico` via
  `iconbitmap` (nativo da taskbar); macOS/Linux usam `edp_128.png` via
  `iconphoto`. Cada passo em `try/except` — ícone ausente **não** quebra a GUI.
  `edp.ico` (16–256 px) foi gerado dos PNGs e vive em `assets/icons/`.
- **Sem hipótese de SO na GUI**: nada de `osascript`, caminhos absolutos de
  macOS ou `"/"` hardcoded; `os.path.join`/`os.pathsep` em todo lugar.
- `pyproject.toml`: `classifiers` com `Operating System :: OS Independent`;
  `package-data` `assets/icons/*` cobre o `.ico`.

## Armadilhas conhecidas

- **Tk 8.5 no macOS é quebrado**: `/usr/bin/python3` (Tk 8.5 da Apple) abre
  janela vazia em macOS recente. `run-gui.py` (via `run-gui.sh`) escolhe um
  Python com Tk ≥ 8.6 (Homebrew `python-tk@3.12` → Tk 9.x, ou python.org →
  8.6). Env `EDP_PYTHON` tem prioridade; `--print` só diagnostica.
- **Perda de dados em FS case-insensitive (APFS)**: dois caminhos com caixa
  diferente podem ser o MESMO arquivo. Barrado no **core** (`_validate_paths` →
  `os.path.samefile`), antes de qualquer cópia; a GUI não duplica esse guard.
- **Sufixo de saída**: o botão gera ESR + FreeDVDBoot, então o nome sugerido usa
  `_fdvdb.iso` (alinhado ao `edp fdvdb` da CLI). O nome é derivado pelo helper
  único `src/edp/paths.py:default_output_path` (compartilhado com a CLI).

## Bundle macOS (`EDP.app`)

- Estrutura: `Contents/{Info.plist, MacOS/{EDP,launcher}, Resources/edp.icns}`.
  `CFBundleExecutable = launcher` (script sh) que faz `exec "$HERE/EDP" -m edp.gui`.
- **NÃO é autônomo**: `Contents/MacOS/EDP` é uma **cópia** de um Python do
  Homebrew (33 KB, thin arm64) que linka o framework em caminho absoluto
  (`/opt/homebrew/Cellar/python@3.12/...`) via `_Py_BytesMain`. E o `launcher`
  depende de `<repo>/src` por caminho relativo `EDP.app/../..`.
  - Consequência: o `.app` **precisa ficar na raiz do repositório**; movido,
    o launcher avisa (`osascript` alert) e sai. Só roda onde há aquele Python.
  - `codesign`: **não assinado** → Gatekeeper pode bloquear em outra máquina.
- `Info.plist` `CFBundleIconFile = edp.icns` (ícone do Dock). `iconphoto` na GUI
  cobre só a janela/barra de título.
- Distribuição autônoma exigiria empacotador (PyInstaller) — fora do escopo
  (ADR-0004, sem dependências de runtime).

## Assets e empacotamento

- `src/edp/assets/`: `dvd_video_data.bin`, `fdvdb/` (3 payloads) e
  `icons/` com `edp.icns` + `edp.ico` + PNGs 16..1024 + `icon.svg`. No código,
  `edp_128.png` (janela, macOS/Linux) e `edp.ico` (Windows) são os usados; os
  demais são fonte para os ícones e documentação.
- `pyproject.toml` `package-data = ["assets/*.bin", "assets/fdvdb/*",
  "assets/icons/*"]` cobre todos os assets (o `icons/*` já inclui o `.ico`).
  Scripts: `edp` → `edp.cli:main`; `edp-gui` → `edp.gui.app:main`.

## Verificação rápida (sem abrir janela pendurada)

```bash
cd <repo>
PYTHONPATH=src python3 -m py_compile src/edp/gui/app.py src/edp/gui/__main__.py run-gui.py
python3 run-gui.py --print            # diagnostico de interpretador/Tk
bash -n run-gui.sh ; bash -n EDP.app/Contents/MacOS/launcher
PYTHONPATH=src python3 -c "import edp.gui.app as g; print(hasattr(g,'EdpApp'))"
# headless smoke: cria a janela, exercita _set_busy e destroi (sem mainloop)
```

`run-gui.bat` (Windows) é CRLF; valide o conteudo, mas a execucao real só em
Windows (risco residual).
