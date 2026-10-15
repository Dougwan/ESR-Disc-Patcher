# ADR-0004 — Sem dependências de runtime no core

- **Status:** Aceito
- **Data:** 2026-10-14

## Contexto

Alternativas comuns seriam `pycdlib` (parsing ISO/UDF) e `CustomTkinter`/`PyQt`
(GUI).

## Decisão

- O **core não depende de nenhum pacote externo**. O mínimo de ISO9660/UDF
  necessário é implementado internamente (poucas centenas de linhas, testáveis).
- A **GUI** usa `tkinter` (stdlib). Um tema `CustomTkinter` é melhoria opcional,
  fora do caminho crítico.

## Justificativa

- O ESR precisa apenas de offsets fixos e CRC — não de um parser UDF completo.
- Evita "dependência de 10 MB de biblioteca para 200 linhas de lógica".
- Reduz risco de supply-chain e de incompatibilidade de versões.
- O asset binário `dvd_video_data.bin` (24 576 bytes) é versionado no repo com
  SHA-256 registrado, pois é dado, não código.

## Consequências

- Precisamos manter nós mesmos o parsing mínimo de ISO9660 (coberto por testes).
- Se um dia surgir necessidade de UDF completo, `pycdlib` entra como dependência
  **opcional** atrás de um adaptador, sem quebrar o core.
