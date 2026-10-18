# Notebook — Core (domínio / iso / patcher / cli)

Notas operacionais reutilizáveis do backend. Escopo: `src/edp/domain/**`,
`src/edp/iso/**`, `src/edp/patcher/**`, `src/edp/cli.py`, `src/edp/__init__.py`,
`src/edp/__main__.py`, `tests/**`.

## Contrato estável (NÃO quebrar sem coordenação)

Consumido por GUI e CLI:
`EsrService.analyze | make_fdvdb_image | patch_to_new_file | patch_in_place |
unpatch_to_new_file | unpatch_in_place` e os tipos `IsoAnalysis`, `FdvdbReport`,
`EsrError`. GUI só importa `EsrError`, `IsoAnalysis`, `EsrService` (não usa
internals de domain/patcher). `PatchReport.targets`/`dvd_video_lba`/`image_size`
são públicos mas não consumidos internamente — não removidos por risco de API.

## Invariantes do formato (confirmados contra referências)

ESR (verificado byte a byte contra `ali-raheem/esrtool` → `src/lib.rs`):
- Detecção de "já patchado": `LBA 14 * 2048 + 25` contém `b"+NSR"` (4 bytes).
- Patch: `copy LBA34→14`, `copy LBA50→15`; em 34 e 50: `byte[188]=0x80`,
  `byte[189]=0x00`; recomputa `DescriptorCRC` (bytes 8–9 = CRC-16/XMODEM de
  `block[16 : 16+crc_len]`) e `TagChecksum` (byte 4 = `sum(block[0:16]) - block[4]`
  mod 256); grava 12 setores (24576 B) de DVD-Video no LBA 128.
- Unpatch: `copy 14→34`, `copy 15→50`, zero em 14/15 e em 128..139. Reversão
  perfeita **só** para ISO ESR puro (não remove overlay FreeDVDBoot).
- CRC-16/XMODEM: poly 0x1021, init 0, sem reflexão/final-xor. `esrtool` usa a
  mesma tabela; batem.

FreeDVDBoot (verificado contra as notas do CTurt `freedvdboot.html`):
- `VIDEO_TS.BUP` → `VTS_01_0.IFO` (rename do File Identifier, mesmo tamanho).
- `f0 07 00 00 0a 00` → `00 38 00 00 0a 00` (VIDEO_TS.IFO size 2032→14336).
- `f0 07 00 00 0b 00` → `00 30 00 00 11 00` (VTS_01_0.IFO size 12288 + LBA).
- `0x45000` VIDEO_TS.IFO (14336 B), `0x48800` VTS_01_0.IFO (12288 B),
  `0x4B800` loader ELF. Só se aplica sobre disco já ESR-patchado (guard via
  `_replace_all`, que falha se o padrão não existir).

Geometria: setor 2048 B; região do patch = primeiros ~288 KB. `MIN_IMAGE_SIZE`
= `(128+12)*2048` = 286720 cobre LBAs 34/50/14/15/128..139.

## Decisões / invariantes de código

- Camadas: `domain` puro (sem I/O) → `iso` (device/udf/iso9660) → `patcher`
  (descriptor/dvd_data/engine/fdvdb/service) → `cli`/`gui`. Nunca inverter.
- Aritmética binária do patch mora só em `descriptor.py` (pura, testável).
- `EsrPatchEngine` opera sobre `RandomAccessDevice` (DIP): mesmo código p/ arquivo
  e memória. Patch/unpatch in-place exigem flush; service copia antes por padrão.
- Cópia por streaming (1 MiB) com callback de progresso; a origem nunca é tocada
  no modo padrão.

## Armadilhas confirmadas (e correções aplicadas)

- **Espaço temporal perigoso em `patch()`**: a marca `+NSR` aparece logo após
  `copy 34→14` (passo 1); falha entre passos deixa imagem *marcada* mas não
  totalmente patchada. Por isso o `service` sempre copia antes (padrão) e faz
  unlink da saída parcial em qualquer falha.
- **Saída parcial**: copiar fora do `try` deixava parcial em disco se a cópia
  falhasse no meio. Corrigido: cópia dentro do `try` + `_safe_unlink`.
- **Mesmo arquivo em FS case-insensitive (APFS)**: comparar só `abspath`
  deixava passar `jogo.iso` vs `JOGO.ISO` apontando para o mesmo inode → o
  `open(dst,"wb")` truncaria a origem. Corrigido com `os.path.samefile`
  (fallback para `abspath` quando o destino não existe).
- **Erros de E/S crus**: `OSError`/`FileNotFoundError` vazavam da camada e
  viravam traceback na CLI/GUI. Agora convertidos para `PathError` no `service`
  (+ rede de segurança `OSError` no `cli.main`).
- **Inspeção best-effort**: `IsoInspector` captura `EsrError` (não só
  `ElfFormatError`) ao ler ELF/SYSTEM.CNF: imagem truncada vira aviso, não
  aborta a análise.
- **`_parse_dir_record`**: recorte mais curto que o `length` declarado podia
  causar `IndexError`; agora retorna `None`.

## Portabilidade (macOS/Linux/Windows)

Modo escolhido: **o codigo-fonte roda nos 3 SOs** com Python 3.9+ (com Tk).
Sem binario standalone e sem dependencia de runtime (so stdlib).

### Já era portável (verificado, sem mudança)
- I/O de dados sempre binário: `open(..., "rb"/"wb"/"r+b")` (`service` 201/217,
  `device` 38, `fdvdb` 64/109, `dvd_data` 28). `FileDevice` só aceita modos binários.
- Texto do disco decodificado com encoding explícito, nunca pelo locale:
  SYSTEM.CNF em `latin-1` (`system_cnf` 25), nomes ISO em `latin-1`
  (`iso9660` 55/71), NSR em `ascii` (`udf` 24).
- Assets localizados por caminho relativo ao pacote (`__file__`), não ao cwd:
  `dvd_data.py` 16-20, `fdvdb.py` 43-45.
- Caminhos montados com `os.path.join`/`getcwd`; sem `~`/home assumido
  (`fdvdb.override_dir`), sem suposição de separador.
- Sem `signal`/`os.fork`/`fcntl`/`termios`/POSIX-only; `KeyboardInterrupt` já
  tratado em `cli.main`.
- Strings de diagnóstico (`patch_state`, `region`) são ASCII por construção.

### Ajustado
- **`service._same_file`** (arquivo:172): quando o destino não existe o
  `samefile` (inode) falha e caía em `abspath(a)==abspath(b)`, sensível à caixa.
  Novo `_path_key()` = `normcase(normpath(abspath()))`: no Windows dobra caixa e
  uniformiza separador/`..`; em POSIX é identidade. `pathmod` injetável para
  validar a semântica NTFS via `ntpath` rodando em macOS. Caso "destino não
  existe" preservado (só troca a comparação).
- **`cli._print_progress`**: em stderr não interativo (`isatty()` falso, ex.
  pipe/redirecionamento/cmd.exe legado) o `\r` não redesenha; agora emite linhas
  periódicas a cada 10% + 100%. Em terminal mantém o `\r` atual.
- **Saída ASCII-segura** (`cli._write_safe`/`_emit`): strings derivadas da
  imagem (Volume ID/nome decodificado em latin-1, caminhos) podiam conter code
  points que a code page do console (cp1252/cp437) não representa → o
  `UnicodeEncodeError` derrubava a CLI. Agora, na falha de encode, reescreve com
  `errors="replace"`; UTF-8 passa intacto.
- **`paths.default_output_path`**: passa a reconhecer `/` **e** `\` como
  separador e aplica `splitext` só ao componente final, para que um ponto no
  diretório (`C:\my.dir\jogo`) não seja tratado como extensão. Assinatura
  inalterada (contrato da GUI).

### Armadilhas / riscos residuais
- `default_output_path` trata `\` como separador também em POSIX: um arquivo
  POSIX com `\` literal no nome tem derivação diferente (caso patológico).
- `normcase` em macOS é identidade (POSIX); a comparação case-insensitive no
  fallback só vale de fato no Windows. Em APFS o caso case-insensitive já é
  coberto pelo `samefile` quando o destino existe.
- Confirmação definitiva em Windows/Linux (console cp1252 real, NTFS, paths
  UNC/longos) só na máquina alvo; a suíte valida a lógica via `ntpath`/`cp1252`.

## Verificação

```bash
cd <repo>
PYTHONPATH=src python3 -m unittest discover -s tests -t . -v   # 91 testes
PYTHONPATH=src python3 -m edp --help
PYTHONPATH=src python3 -c "import edp, edp.cli, edp.paths, edp.patcher.service, edp.iso.inspector"
```

Lógica portável coberta em `tests/test_portability.py` (20 testes):
`_path_key`/`_same_file` (via `ntpath`/`posixpath`), `default_output_path`
(caminhos Windows), `_print_progress` (tty e não-tty), `_write_safe`
(cp1252/ascii/utf-8) e decodificação latin-1 do SYSTEM.CNF.

## Itens de coordenação (fora do escopo backend)

- **[resolvido]** helper de nome de saída agora único em `src/edp/paths.py`
  (`default_output_path`), usado por `cli.py` e `gui/app.py` (fim da duplicação).
- `PatchReport` carrega campos sem consumidor interno; reduzir é decisão de API.
- **[resolvido] Teste em hardware real**: boot confirmado em console stock em
  2026-10-17 — ver "Validação em hardware real" abaixo.

## Validação em hardware real (2026-10-17)

Primeiro boot confirmado em **console real** (PS2 stock, `English`, sem modchip):
discos gerados por `edp fdvdb` (ESR + FreeDVDBoot, loader embutido `dccbaaee`)
**bootaram os jogos**.

- **Discos de teste**: `Way of the Samurai 2 ..._fdvdb.iso` (1,43 GiB) e
  `Max Payne (Brazil)_fdvdb.iso` (2,73 GiB), gravados em DVD-R a **4x**,
  finalizados e verificados.
- **Disco de controle** (já funcional, não gerado por nós): DVD-R de ICO
  (`SCUS_974.72`) — a região de payload **LBA 128–161 é byte-idêntica** à nossa
  saída, loader `dccbaaee` inclusive → prova que payload/loader do pacote são
  válidos.
- **Causa raiz das falhas anteriores**: **gravação ruim** (gravador USB
  `hp UJ8E1` caindo por energia), **não** o EDP. O GH3 (4,03 GiB) falhou com
  gravações interrompidas; os ISOs analisam como `patched`/`SLUS_216.72`.
- **Mapa do que o EDP altera**: 18 231 bytes em 35 setores, todos em LBA 14–158
  (14/15 e 34/50 = ESR; 128+ = DVD-Video/overlay FreeDVDBoot; 151–158 = loader
  ELF). O resto da ISO permanece byte a byte igual ao original.

Fator dominante de falha na prática: **gravação/mídia** (dye barato, gravador
instável, velocidade alta), não a ferramenta.
