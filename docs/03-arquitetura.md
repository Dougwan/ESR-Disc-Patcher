# Fase 1.3 — Arquitetura

## Princípios

- **Separação de camadas** por responsabilidade e dependência unidirecional:
  `domain` (puro) ← `iso` ← `patcher` ← `service` ← (`cli` | `gui`).
- **Clean Code / SOLID**:
  - *SRP* — cada módulo faz uma coisa (CRC, header ELF, ISO9660, UDF, engine...).
  - *OCP* — a engine opera sobre uma abstração `RandomAccessDevice`; novos
    backends (arquivo, memória, dispositivo) são plugáveis sem alterar a engine.
  - *LSP/ISP* — interfaces pequenas (`ReadableDevice`, `WritableDevice`).
  - *DIP* — a engine depende de `Protocol`, não de `File`. A GUI/CLI dependem
    do serviço, que depende da engine, que depende do domínio.
- **Sem código monolítico**: nada de "classe faz-tudo". O domínio não importa
  `io`, `os` nem `tkinter` (exceto no carregamento do asset embutido).

## Mapa de dependências

```
                    ┌────────────────────────────┐
        cli ─────►  │            service          │  ◄───── gui
                    │  (orquestra cópia+progresso)│
                    └──────────────┬─────────────┘
                                   │
                    ┌──────────────▼─────────────┐
                    │        patch engine         │
                    │  patch / unpatch em Device  │
                    └───────┬───────────┬────────┘
                            │           │
                 ┌──────────▼──┐  ┌─────▼──────────┐
                 │ descriptor  │  │ dvd_data       │
                 │ (CRC/checksum)│ │ (blob embutido)│
                 └──────┬──────┘  └────────────────┘
                        │
        ┌───────────────▼───────────────────────────────┐
        │                    iso layer                    │
        │  device (Protocol, FileDevice, MemoryDevice)     │
        │  udf (detecção)   iso9660 (PVD+dir)  inspector   │
        └───────────────────────┬────────────────────────┘
                                │
                    ┌───────────▼───────────┐
                    │       domain (puro)     │
                    │ constants, errors,     │
                    │ models, crc, elf,      │
                    │ system_cnf             │
                    └────────────────────────┘
```

Dependência aponta sempre para baixo. `domain` não conhece `iso`; `iso` não
conhece `patcher`.

## Contratos principais

### `domain`

- `crc.crc16_xmodem(data, length=None) -> int`
- `elf.parse_elf_header(data) -> ElfHeader` · `elf.validate(...) -> list[str]`
- `system_cnf.parse_system_cnf(text) -> SystemCnf`
- `models`: `UdfInfo`, `ElfHeader`, `SystemCnf`, `GameInfo`, `IsoAnalysis`,
  `PatchReport`, dataclasses imutáveis.
- `errors`: hierarquia `EsrError` → `NotUdfError`, `AlreadyPatchedError`,
  `NotPatchedError`, `IsoStructureError`, `ElfFormatError`,
  `DeviceError`, `PathError`.

### `iso`

- `device.RandomAccessDevice` — `Protocol`: `size`, `read_at(off, n)`,
  `write_at(off, data)`, `flush()`.
- `device.FileDevice(path, mode)` — implementa sobre arquivo real.
- `device.MemoryDevice(initial: bytes)` — em memória (testes).
- `udf.find_volume_recognition(device) -> UdfInfo | None`
- `udf.looks_patched(device) -> bool`
- `iso9660.read_pvd(device)`, `RootDirectory.list_entries()`,
  `find_file(name)`.
- `inspector.IsoInspector.analyze(device) -> IsoAnalysis` — junta UDF+ISO9660+
  ELF+SYSTEM.CNF.

### `patcher`

- `descriptor.patch_directory_descriptor(block: bytes, target_lba: int) -> bytes`
  — pura, sem I/O; aplica `bytes[188..190]` + CRC + checksum.
- `descriptor.update_checksums(block) -> bytes`
- `dvd_data.load_dvd_video_data() -> bytes` (lê o asset embutido, valida
  tamanho/SHA).
- `engine.EsrPatchEngine(device)` — `patch()`, `unpatch()`, `is_patched()`,
  `validate_layout()`.
- `service.EsrService` — casos de uso de alto nível:
  `analyze(path)`, `patch_to_new_file(src, dst, progress=None)`,
  `unpatch_to_new_file(...)`, `patch_in_place(path, progress=None)`.

## Fluxo do caso de uso principal

```
analyze(entrada)
    ├─ abre como RandomAccessDevice (read)
    ├─ inspector: UDF? já patchado? ISO9660 PVD? SYSTEM.CNF? ELF do boot?
    └─ retorna IsoAnalysis (game id, estado, avisos)

patch_to_new_file(entrada, saida)
    ├─ analyze(entrada)              → valida (UDF, não patchada)
    ├─ cópia em streaming com progresso (shutil.copyfileobj + callback)
    ├─ abre saída como FileDevice (r+b)
    └─ engine.patch()                → LBAs 14/15/34/50/128 + CRC
```

## Decisões de arquitetura (ADRs)

- `docs/adr/0001-linguagem-python.md`
- `docs/adr/0002-alvo-do-patch-e-udf.md`
- `docs/adr/0003-modo-copia-vs-in-place.md`
- `docs/adr/0004-sem-dependencias-de-runtime.md`

## Estratégia de testes (Fase 2)

- **Unitário (domínio puro):** CRC contra vetores conhecidos; header ELF
  válido/inválido; parsing de `SYSTEM.CNF` (com/sem `;1`, comentários, `BOOT2`);
  `descriptor.patch_directory_descriptor` idempotente e com CRC verificado.
- **Integração (sem hardware):** construir uma **ISO sintética** em memória
  (VRS UDF + PVD ISO9660 + `SYSTEM.CNF` + ELF fake) e rodar o fluxo
  `analyze` → `patch` → `analyze` → `unpatch`, conferindo bytes de controle.
- **Golden:** comparar a ISO sintética patchada byte a byte com o resultado
  esperado calculado manualmente.

## Lacunas declaradas

- Não há (nem deve haver) etapa de **compilação de imagem** (`mkisofs`): o ESR
  não recompõe o filesystem, apenas ajusta descritores. O documento do briefing
  fala em "camada de compilação de imagem"; ela **não é necessária** para o
  patch ESR e por isso não existe no escopo. Se o objetivo futuro for *criar* um
  disco DVDV-diretos do zero (homebrew), aí sim seria preciso `mkisofs`/`pycdlib`
  — módulo novo, não parte do patch.
- A suíte cobre toda a lógica determinística. A validação definitiva é o **boot
  em hardware real** — feita manualmente e **confirmada em 2026-10-17** (PS2
  stock, discos gerados por `edp fdvdb`, mídia DVD-R gravada a 4x, inclusive um
  disco de 4,03 GiB quase cheio). Ver `README.pt-BR.md`, seção "Validação em
  hardware real".
