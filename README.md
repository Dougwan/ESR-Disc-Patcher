# ![EDP](src/edp/assets/icons/edp_128.png) EDP — ESR Disc Patcher

[![Licença: GPL-3.0-or-later](https://img.shields.io/badge/licen%C3%A7a-GPL--3.0--or--later-blue)](LICENSE)
![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white)
![Plataformas: macOS | Linux | Windows](<https://img.shields.io/badge/plataformas-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey>)
![Dependências: 0 em runtime](<https://img.shields.io/badge/depend%C3%AAncias-0%20em%20runtime-success>)
![AI-assisted](<https://img.shields.io/badge/AI--assisted-8A2BE2>)

Transforme a ISO do seu próprio jogo de PS2 em um disco que o console aceita e
inicia, sem modchip.

---

## O que é

O **EDP** aplica (e remove) o **patch ESR** em imagens de disco (ISO) de
PlayStation 2. O console só aceita mídia gravada se o disco se apresentar como
algo que o leitor reconheça — e é exatamente isso que o EDP prepara. A
ferramenta é um utilitário de **backup, preservação e homebrew**: você informa a
ISO, ela gera uma nova imagem pronta para gravar, e o console a boota pelo
loader **ESR**.

## Como funciona

Pense no disco como um **envelope**. O console não lê o conteúdo: ele
**inspeciona a etiqueta** do envelope e decide se aceita. O EDP reescreve essa
etiqueta (os *descritores* do disco) para que o console o trate como um
**DVD-Video**, gesto que o leitor reconhece. **O executável do jogo não é
alterado** — o jogo em si continua byte a byte como era.

Há dois caminhos de boot:

- **Boot direto (ESR + FreeDVDBoot):** o disco já embute o exploit e o loader;
  o console inicia **sem modchip e sem instalar nada**. (Requer compatibilidade
  de hardware — ver abaixo.)
- **Modo clássico:** o disco é aceito pelo leitor, mas o boot depende de o
  **loader ESR já estar instalado no console** (por exemplo, via FreeMcBoot).

Por padrão **a ISO original nunca é alterada**: a saída é sempre um arquivo
novo. Existe um modo destrutivo (`--in-place`), mas ele é opcional e não é o
caminho padrão.

## Uso responsável

1. **Uso pretendido:** backup e preservação dos **seus próprios discos** e
   execução de **homebrew**.
2. A ferramenta **não distribui conteúdo protegido**: inclui apenas componentes
   open-source e um bloco estrutural. Ela **não** faz *ripping* nem download de
   jogos.
3. A legalidade de backup e *format-shifting* **varia por jurisdição** — use
   apenas onde for permitido pela sua lei local.
4. **Você é o único responsável** pelo uso da ferramenta.
5. **Não há garantia de compatibilidade.** O resultado depende do modelo,
   firmware e região do console, e de o loader ESR estar presente (modo
   clássico) ou de o boot direto ser compatível com o seu aparelho.

## Requisitos

O EDP roda a partir do **mesmo código-fonte** em macOS, Linux e Windows — **sem
binário por plataforma** e **sem dependências de runtime** (somente biblioteca
padrão do Python):

- **Python 3.9+** (a CLI funciona em qualquer Python 3.9+).
- A **GUI** exige `tkinter` com **Tk ≥ 8.6**.

Por sistema operacional:

- **macOS:** Python 3.9+. O Python do sistema (`/usr/bin/python3`) traz o **Tk
  8.5** da Apple, quebrado em versões recentes (janela abre vazia) — para a GUI
  use um interpretador com Tk ≥ 8.6 (`brew install python-tk@3.12` ou o
  instalador do [python.org](https://www.python.org/)).
- **Linux:** Python 3.9+. O `tkinter` costuma vir em pacote separado para a GUI:
  `sudo apt install python3-tk` (Debian/Ubuntu), `sudo dnf install python3-tkinter`
  (Fedora) ou `sudo pacman -S tk` (Arch).
- **Windows:** Python 3.9+ do
  [python.org](https://www.python.org/downloads/windows/) (marque *tcl/tk and
  IDLE*); a GUI já vem com o Tk no instalador oficial.

Detalhes e a matriz completa em [`docs/04-portabilidade.md`](docs/04-portabilidade.md).

> Os exemplos usam `python3`. No Windows troque por `py -3` (ou `python`) — vale
> para todos os comandos deste README.

## Instalação

Não precisa instalar. Aponte o `PYTHONPATH` para `src` e rode direto do fonte:

```bash
PYTHONPATH=src python3 -m edp info jogo.iso
```

Ou instale, o que cria os comandos `edp` e `edp-gui` no `PATH`:

```bash
python3 -m pip install .        # instala; use -e . para modo editável
```

## Uso — GUI

A GUI é a mesma nos três sistemas. Passo a passo:

1. Inicie a interface (qualquer uma destas formas):
   - `python3 run-gui.py` — forma direta (macOS / Linux / Windows);
   - `./run-gui.sh` (macOS / Linux) ou `run-gui.bat` (Windows) — atalhos;
   - `edp-gui` — se você instalou com `pip install .`.
2. Clique em **Selecionar...** e escolha a sua ISO. O **diagnóstico** aparece
   automaticamente (UDF, estado do patch, game ID, região, ELF de boot).
3. Confira o **arquivo de saída** sugerido (por padrão `<nome>_fdvdb.iso`) e
   ajuste com **Salvar como...** se quiser.
4. Clique em **Aplicar patch** e acompanhe a barra de progresso. O botão gera
   o **disco de boot direto** (ESR + FreeDVDBoot), com os payloads/loader já
   embutidos — não há nada para configurar.
5. Ao concluir, a GUI mostra a saída gerada e a reanalisa. A **ISO original é
   sempre preservada** (a saída é um arquivo novo).

Atalhos e interpretador preferido:

```bash
./run-gui.sh                                          # macOS / Linux
run-gui.bat                                           # Windows
python3 run-gui.py --print                            # só diagnóstico, não abre janela
EDP_PYTHON=/caminho/python3 ./run-gui.sh              # macOS / Linux (força o interpretador)
set EDP_PYTHON=C:\caminho\python.exe && run-gui.bat   # Windows (força o interpretador)
```

No **macOS** há ainda o bundle `EDP.app/`, uma conveniência para abrir a GUI
pelo Finder/Dock. Ele **não é autônomo nem portátil** e precisa ficar na raiz do
repositório — detalhes em
[`docs/04-portabilidade.md`](docs/04-portabilidade.md).

## Uso — CLI

```bash
# Inspeciona a imagem sem alterá-la (UDF, estado do patch, game id, ELF)
PYTHONPATH=src python3 -m edp info jogo.iso

# Aplica o patch ESR gerando uma nova ISO (preserva a original) — padrão
PYTHONPATH=src python3 -m edp patch jogo.iso -o jogo_esr.iso

# Gera o disco de boot direto (ESR + FreeDVDBoot)
PYTHONPATH=src python3 -m edp fdvdb jogo.iso -o jogo_fdvdb.iso

# Remove o patch ESR (reversão — só na CLI; ver nota abaixo)
PYTHONPATH=src python3 -m edp unpatch jogo_esr.iso -o jogo_original.iso
```

Saídas padrão quando `-o` é omitido: `patch` → `<nome>_esr.iso`, `fdvdb` →
`<nome>_fdvdb.iso`, `unpatch` → `<nome>_unpatched.iso`. `patch` e `unpatch`
aceitam `--in-place` (destrutivo, altera o próprio arquivo) e todos aceitam
`--overwrite` (sobrescreve a saída existente).

> **Sobre `unpatch`:** ele desfaz o **patch ESR** (restaura os descritores e
> zera a área DVD-Video) — reversão perfeita em ISOs só-ESR. Ele **não** remove
> o overlay **FreeDVDBoot** (os payloads em LBA 138/145/151 permanecem). Por
> isso existe **só na CLI**: a GUI sempre gera um arquivo novo e preserva a
> original, tornando o unpatch desnecessário lá.

## Boot direto (FreeDVDBoot + ESR)

Além do patch ESR clássico — que depende do loader ESR no console —, o EDP gera
um disco **auto-bootável** combinando o ESR com o exploit **FreeDVDBoot**. O
disco gravado boota num PS2 **sem modchip e sem nada instalado**, sujeito à
compatibilidade do exploit.

Requisitos do exploit (não da ferramenta):

- **Slim** → qualquer um (payload híbrido 3.10/3.11); **Phat** → apenas 2.10,
  2.12 e 3.04;
- console configurado em **English**.

```bash
PYTHONPATH=src python3 -m edp fdvdb jogo.iso -o jogo_fdvdb.iso
```

Os payloads/loader usados são os **embutidos no pacote**. Para usar outros (por
exemplo, o firmware de **Phat** 2.10/2.12/3.04), a CLI aceita as flags
`--video-ts-ifo`, `--vts-01-0-ifo` e `--loader`, ou uma pasta de override
(`EDP_FDVDB_DIR` ou `payloads/` ao lado do projeto); os embutidos são o padrão.
A GUI detecta a pasta de override automaticamente.

## FAQ e limitações

- **Gravei, mas o console não boota.** Verifique: a ISO era um jogo PS2
  ISO9660+UDF válido; no modo clássico, o loader ESR está instalado no console;
  no boot direto, o seu modelo existe na lista suportada (Phat só 2.10/2.12/3.04)
  e o console está em **English**.
- **Modo clássico x boot direto.** Sem loader no console, use `fdvdb` (boot
  direto). Com loader ESR já instalado, `patch` basta.
- **Remoção do patch.** Só o `unpatch` na CLI desfaz o patch ESR; ele não
  remove o overlay FreeDVDBoot.
- **Não há garantia de compatibilidade** com todo modelo/firmware/região — não
  prometemos "funciona em qualquer PS2".
- **A ISO original é preservada por padrão.** O modo `--in-place` é destrutivo e
  existe apenas para quem sabe o que está fazendo.

## Referência técnica

### Algoritmo do patch (ESR)

1. backup do LBA 34 → 14 e do LBA 50 → 15;
2. `bytes[188..190]` dos descritores dos LBAs 34 e 50 ← LBA 128;
3. recálculo do **CRC-16/XMODEM** (bytes 8–9) e do *checksum* do *tag* UDF
   (byte 4);
4. escrita de **24 576 bytes** (12 setores) de estrutura DVD-Video no LBA 128.

Marca de "já patchado": `+NSR` em `LBA 14 * 2048 + 25`. Toda a região manipulada
fica nos primeiros ~288 KB (`128 * 2048 + 24576 = 286 720`), então o patch é
O(1) — não é preciso carregar os GB da ISO. O ELF do jogo e o `SYSTEM.CNF`
permanecem intactos. Ver [`docs/01-analise-do-problema.md`](docs/01-analise-do-problema.md)
e [`docs/adr/0002-alvo-do-patch-e-udf.md`](docs/adr/0002-alvo-do-patch-e-udf.md).

### Overlay de boot direto (FreeDVDBoot)

Numa passada sobre a imagem: ESR patch → renomeia `VIDEO_TS.BUP` →
`VTS_01_0.IFO` → ajusta os *short_ad* → grava os 3 arquivos em
`0x45000`/`0x48800`/`0x4B800` (LBAs 138/145/151).

### Arquitetura

```
domain  → crc, elf, system_cnf, models, errors, constants, gameid
iso     → device (Protocol/File/Memory), udf, iso9660, inspector
patcher → descriptor, dvd_data, engine, service
cli/gui → apresentação sobre o service
```

A dependência aponta sempre para baixo; o `service` orquestra cópia e
progresso e é a única porta usada por CLI e GUI. Ver
[`docs/03-arquitetura.md`](docs/03-arquitetura.md) e as decisões registradas em
`docs/adr/0001..0004`.

### Testes

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -t . -v
```

Cobrem o domínio (CRC, ELF, `SYSTEM.CNF`), a camada ISO (UDF, ISO9660), a
transformação do descritor e um fluxo de integração completo
(`analyze → patch → analyze → unpatch`) sobre uma ISO sintética. A validação
definitiva em hardware real (console + mídia gravada) está fora do escopo
automatizado.

### Procedência dos assets

Bloco de estrutura DVD-Video embutido no pacote:

- `src/edp/assets/dvd_video_data.bin` — 24 576 bytes, SHA-256
  `d61083e8bc90a959c21958e46216a8531c2095c2f6f780b779d9489f3fd5a845`.

Payloads/loader de FreeDVDBoot (`src/edp/assets/fdvdb/`, extraídos de
`FDVDB_ESR_Patcher_v0.4` / "FreeDVDBoot Auto Patcher"):

- `payload_VIDEO_TS.IFO` — 14 336 bytes, SHA-256
  `e4a41769d71989ca40b4c64a79cf8c5b6b695cb1779af71cd2978f00329f37d6`
  (exploit recompilado com `LOAD_FROM_SECTOR_RELATIVE_TO_VIDEO_TS_IFO`,
  diferente do do repositório do CTurt);
- `payload_VTS_01_0.IFO` — 12 288 bytes, SHA-256
  `c26206e1e4f4405855495037eb725a9be0bb964d2d163fd712edd30e626fd3c0`;
- `esr.elf` — 14 921 bytes, SHA-256
  `dccbaaee464ced9bbd62f25db7c4e02b549be6f4e7705fddb5ff970ba1403fa4`
  (loader ESR de ffgriever, ELF PS2 válido).

Todos versionados no repositório para garantir reprodutibilidade.

### Ícone

`src/edp/assets/icons/` — a **face de dados** do disco (a parte cinza que o
laser lê), em pixel art grayscale (grade 32×32, contorno preto, brilho diagonal
e hub com furo central): `icon.svg` (vetorial, para edição),
`edp_16/32/128/256/512/1024.png` (com alpha; o de 128 é o usado no `iconphoto`
da GUI), `edp.ico` (Windows) e `edp.icns` (macOS). Desenhado pelo projeto
(GPL-3.0); não usa logotipo/marca PlayStation.

A GUI aplica o ícone por sistema: **Windows** usa `edp.ico` via `iconbitmap`;
**macOS/Linux** usam `edp_128.png` via `iconphoto`; se algum asset faltar, a GUI
abre normalmente (o ícone é cosmético). No macOS o ícone do Dock/Finder vem do
bundle `EDP.app/`. Ver `src/edp/gui/app.py` e
[`docs/04-portabilidade.md`](docs/04-portabilidade.md).

## Créditos e licença

Distribuído sob a **[GPL-3.0-or-later](LICENSE)**.

Ideia e patch ESR inspirados nas ferramentas open-source de referência da cena
PS2: **ffgriever** (ESR), **bootsector** (esr patch), **CTurt** (FreeDVDBoot),
**ali-raheem** (esrtool) e **James Pelster** (OpenESRDiscPatcher).
