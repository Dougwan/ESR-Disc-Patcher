# ADR-0002 — O patch ESR altera descritores UDF, não o executável do jogo

- **Status:** Aceito
- **Data:** 2026-10-14
- **Contexto:** o briefing descrevia "injeção do patch binário do ESR no
  executável do jogo".

## Decisão

Implementar o patch ESR exatamente como as ferramentas de referência
(`esr-disc-patcher`, `OpenESRDiscPatcher`, `esrtool`):

1. backup LBA 34 → LBA 14 e LBA 50 → LBA 15;
2. `bytes[188]=0x80`, `bytes[189]=0x00` nos descritores dos LBAs 34 e 50;
3. recálculo de CRC-16/XMODEM (bytes 8–9) e checksum do tag (byte 4);
4. escrita de 24 576 bytes de estrutura DVD-Video no LBA 128.

## Justificativa

O `mechacon` aceita o disco se ele *parecer* um DVD-Video. Isso é obtido
fazendo o descritor de diretório raiz apontar para uma estrutura DVD-Video
sintética. O executável do jogo e o `SYSTEM.CNF` permanecem intactos; quem
boota o jogo é o loader ESR externo.

Foi verificado no código-fonte de três implementações independentes. Alterar o
ELF do jogo não é o mecanismo do ESR e não funcionaria.

## Consequências

- O `SYSTEM.CNF` e o header ELF são usados apenas para **inspeção/pré-checagem**
  (informar o game id, garantir que é a ISO certa), não para o patch.
- Não existe etapa de "compilação de imagem" no escopo (ver ADR de escopo na
  arquitetura).
