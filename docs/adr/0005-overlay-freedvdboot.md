# ADR-0005 — Overlay FreeDVDBoot (`fdvdb`) como feature opcional ao patch ESR

- **Status:** Aceito (documentado retroativamente)
- **Data:** 2026-10-19
- **Contexto:** `src/edp/patcher/fdvdb.py`, `EsrService.make_fdvdb_image`, o
  subcomando `edp fdvdb` e a ação correspondente na GUI foram implementados
  junto com o patch ESR (ADR-0002), mas sem um ADR próprio — ficando de fora
  do contrato documentado em `docs/03-arquitetura.md`.

## Decisão

Manter o overlay FreeDVDBoot como uma **feature opcional e separada**, construída
sobre o mesmo pipeline de cópia (`EsrService._copy_then`), mas como um passo
adicional e independente do patch ESR:

1. aplica o patch ESR normalmente (ADR-0002, sem alterações);
2. em seguida, sobrescreve `VIDEO_TS.IFO`/`VTS_01_0.IFO` e embute um loader ELF
   (`esr.elf`) em `0x4B800`, permitindo boot direto sem instalar o loader ESR
   classico no console;
3. os payloads vêm, em ordem de prioridade: flags explícitas da CLI/GUI →
   diretório de override (`EDP_FDVDB_DIR` ou `./payloads`) → assets embutidos
   no pacote (`src/edp/assets/fdvdb/*`).

## Justificativa

- É um modo de boot **complementar**, não um substituto do mecanismo ESR: o
  disco gerado por `make_fdvdb_image` ainda contém o patch ESR íntegro: a
  única diferença é a adição do overlay DVD-Video/loader por cima.
- Reaproveita a mesma engine (`EsrPatchEngine`) e o mesmo pipeline de cópia
  segura (`_copy_then`), sem duplicar a lógica de precheck/cópia/cleanup.
- Já tem cobertura de testes própria (`tests/test_fdvdb.py`) e foi validado em
  hardware real (ver `.notebook/core.md`).

## Consequências

- `EsrService.make_fdvdb_image` passa a constar no contrato público documentado
  em `docs/03-arquitetura.md` (seção "Contratos principais"), junto com
  `analyze`, `patch_to_new_file`, `unpatch_to_new_file`, `patch_in_place`.
- A frase da ADR-0002 "não existe etapa de compilação de imagem no escopo"
  refere-se ao patch ESR em si (que não "compila" nada, só ajusta descritores
  UDF existentes); o overlay FreeDVDBoot é tratado como uma etapa adicional e
  opcional, fora do escopo mínimo do ESR, não como uma revisão daquela decisão.
- Futuras mudanças no formato dos payloads (`esr.elf`, `VIDEO_TS.IFO`,
  `VTS_01_0.IFO`) devem manter `tests/test_fdvdb.py` verde e atualizar os
  assets em `src/edp/assets/fdvdb/` com o mesmo cuidado dado a
  `dvd_video_data.bin` (ADR-0004): são dados versionados, não código.
