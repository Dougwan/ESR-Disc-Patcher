# Fase 1.1 — Análise do Problema

## Objetivo do produto

Ferramenta de automação que aplica o **patch ESR** em uma imagem de disco (ISO)
de PlayStation 2, de modo que o disco gravado seja aceito pelo `mechacon`
(processador de segurança do PS2) como um **DVD-Video** e, em seguida, bootado
pelo loader **ESR** rodando no console.

## Correção técnica necessária (premissa do briefing)

O briefing descreve o patch como *"injeção do patch binário do ESR no executável
do jogo"*. **Isso não corresponde ao formato real do ESR e precisa ser corrigido
antes de escrever qualquer código**, sob pena de implementar algo que nunca
funcionará no hardware.

O que o ESR Disc Patcher realmente faz (confirmado nas implementações de
referência: `esr-disc-patcher`, `OpenESRDiscPatcher` e `esrtool`):

1. O disco precisa ser **híbrido ISO9660 + UDF** (todo jogo PS2 comercial é).
2. O patch **não toca no executável do jogo (`SLUS_xxx.xx` / `SYSTEM.CNF`)** nem
   reescreve o ELF do jogo.
3. O patch reescreve **descritores de diretório UDF** já existentes (LBAs 34 e
   50) para que o descritor de diretório raiz aponte para uma estrutura de
   **DVD-Video sintética** gravada no LBA 128.

### Passos exatos do patch (algoritmo de referência)

| # | Operação | Detalhe |
|---|----------|---------|
| 1 | Backup do LBA 34 → LBA 14 | guarda o descritor original |
| 2 | Backup do LBA 50 → LBA 15 | guarda o descritor original |
| 3 | Patch do descritor no LBA 34 | `bytes[188]=0x80`, `bytes[189]=0x00` (aponta a extensão para o LBA 128), recalcula CRC e checksum do *tag* UDF |
| 4 | Patch do descritor no LBA 50 | idem |
| 5 | Escreve 24 576 bytes (12 setores) de estrutura DVD-Video no LBA 128 | contém `VIDEO_TS.IFO`/`VIDEO_TS.BUP`, o que faz o disco ser aceito como vídeo |

Recálculos obrigatórios em cada descritor de 2048 bytes:

- **CRC do descritor** (`DescriptorCRC`, bytes 8–9): CRC-16/XMODEM (poly
  `0x1021`, init `0x0000`) sobre `bytes[16 : 16 + crc_len]`, onde `crc_len` é o
  `DescriptorCRCLength` (u16 LE em `bytes[10..11]`).
- **Checksum do tag** (byte 4): soma de `bytes[0..16]` menos o próprio byte 4,
  módulo 256.

### Detecção de estado (compatível com as ferramentas existentes)

- **É UDF?** — varredura da *Volume Recognition Sequence* (ECMA-167): existe um
  setor cujo byte 0 é `0x00` e cujos bytes 1–5 são `NSR02`/`NSR03`.
- **Já patchado?** — bytes `+NSR` em `LBA 14 * 2048 + 25`.

### Consequências de projeto

- Toda a região manipulada está nos **primeiros ~288 KB** do disco
  (`128 * 2048 + 24576 = 286 720`). **Não é necessário carregar nem copiar os
  4 GB** para aplicar o patch — só ler/escrever blocos pontuais.
- O jogo permanece intacto. A tarefa de "ler `SYSTEM.CNF` e validar o header
  ELF" pedida no briefing pertence à **verificação/informação** (e ao caso de
  uso de homebrew em disco DVDV-diretos), não ao mecanismo do patch. O core
  oferece essas funções como *inspeção* e *pré-checagem*, o que dá valor real
  de teste e proteção contra ISO errada.

## Requisitos funcionais (RF)

- RF1 Detectar se a imagem é ISO/UDF válida; rejeitar leiaute inesperado.
- RF2 Detectar se a imagem **já está patchada**; oferecer *unpatch*.
- RF3 Aplicar o patch ESR fielmente (LBAs 14/15/34/50/128).
- Rasterizar/desfazer (unpatch) restaurando os backups.
- RF4 Inspecionar o jogo: ler `SYSTEM.CNF`, resolver o ELF de boot, validar o
  header ELF (magic, classe, endianness, máquina MIPS) e reportar o *game ID*.
- RF5 Produzir uma ISO de saída sem destruir a original (modo cópia) **ou**
  patch in-place opcional.
- RF6 Reportar progresso (para GUI/CLI) e erros claros e tipados.

## Requisitos não-funcionais (RNF)

- RNF1 Determinismo: mesmo input → mesmo output byte a byte.
- RNF2 Interoperabilidade: ISO resultante idêntica à das ferramentas de
  referência (mesmos LBAs, mesmo CRC).
- RNF3 Baixo acoplamento: domínio puro testável sem tocar em disco.
- RNF4 Performance: patch em O(constante), independente do tamanho do disco;
  cópia em streaming.
- RNF5 Portabilidade: macOS/Linux/Windows.

## Riscos

| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| ISO não híbrida (só ISO9660) ou já patchada | patch inválido | detectar e abortar com erro tipado |
| CRC/checksum errado | disco rejeitado no boot | testes golden contra vetores conhecidos |
| Premissa errada do briefing (patch no ELF) | retrabalho total | corrigida neste documento e na ADR-0002 |
| Destruir a ISO original | perda de dados | modo cópia por padrão |
| Região além dos primeiros 288 KB | não | patch é localizado e verificado por limites |
