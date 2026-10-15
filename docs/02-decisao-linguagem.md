# Fase 1.2 — Avaliação Técnica e Decisão de Linguagem

## O que o domínio realmente exige

Antes de comparar linguagens, é preciso medir a carga real do problema:

1. **E/S de bloco posicional** em um arquivo grande (ISOs têm 1–8 GB, às vezes
   dual-layer). O gargalo é disco, não CPU.
2. **Aritmética de bytes trivial**: copiar 2 KB entre offsets fixos, escrever
   ~288 KB, calcular um CRC-16 de poucos KB.
3. **Parsing leve**: header ELF (64 bytes), `SYSTEM.CNF` (texto minúsculo),
   ISO9660 (PVD + *directory records*).
4. **GUI desktop** simples: escolher arquivo, mostrar progresso, salvar saída.
5. **Testabilidade** alta (operações determinísticas, fáceis de *golden-test*).

Conclusão importante: **não há requisito de CPU/throughput** que justifique uma
linguagem de sistemas. O trabalho pesado é saturação de disco, que qualquer
linguagem faz com buffers.

## Comparativo

| Critério | Python 3 + stdlib | Rust | Go |
|----------|-------------------|------|----|
| E/S posicional | `seek`/`read`/`write` triviais | `FileExt::read_at` | `ReadAt` |
| Manipulação binária | `int.from_bytes`, `struct` (ótimo) | excelente | ok (verboso) |
| CRC-16/XMODEM | 10 linhas | 10 linhas | 10 linhas |
| Parsing ISO9660/ELF | trivial, stdlib | manual, mais código | manual |
| Iteração/refactor | **muito rápida** | lenta (compile) | média |
| Testes | `unittest` (stdlib!) | `cargo test` | `go test` |
| GUI | `tkinter` (stdlib) / CustomTkinter | egui/Tauri (peso, maturidade) | Fyne (imatura) |
| Distribuição | requer Python | binário único | binário único |
| Dependências de runtime | **zero** (stdlib) | zero | zero |
| Risco de bug de baixo nível | baixo (código é banal) | baixo | médio |

### Análise dos trade-offs

- **Rust** venceria se o gargalo fosse throughput/CPU ou se houvesse parsing
  binário complexo e crítico (ex.: um exploit de buffer overflow). Aqui o
  código é aritmética de bytes e CRC — a segurança de memória do Rust protege
  contra muito pouco que seja relevante. O custo: iteração lenta e ecossistema
  de GUI desktop fraco. **Não compensa** para um utilitário pessoal.
- **Go** oferece binário único e boa concorrência (útil para cópia com
  progresso), mas manipulação binária é mais verbosa e o ecossistema de GUI
  desktop é imaturo. Ganho marginal sobre Python. **Não compensa.**
- **Python**: o patch vira ~200 linhas de domínio puro e testável, a GUI é
  nativa (`tkinter`), e não precisamos de `pycdlib`/`xorriso` porque
  implementamos o mínimo de ISO9660/UDF que precisamos (poucas centenas de
  linhas, totalmente testáveis). Zero dependências de runtime.

**Ponto decisivo:** a parte de E/S em Python é O(tamanho do arquivo) apenas no
*modo cópia*, e mesmo ali usamos `shutil.copyfileobj` com buffer grande — que é
limitado pelo disco. O patch em si é O(1) e roda em microssegundos. Portanto a
"desvantagem de performance" do Python **não se materializa** neste domínio.

## Decisão

**Adotar Python 3.9+ (compatível com o interpretador do sistema), biblioteca
padrão apenas (`struct`, `io`, `unicodedata`, `unittest`, `tkinter`).**

- `pycdlib`/`xorriso` **não são necessários**: o ESR só precisa de offsets
  fixos + CRC; o ISO9660 é implementado minimamente para inspecionar
  `SYSTEM.CNF`.
- `CustomTkinter`/`PyQt`/`Flet` são **opcionais**: a GUI padrão usa `tkinter`
  (nativo, sem instalação). Um tema `CustomTkinter` pode ser plugado depois sem
  tocar no core.

Ver `docs/adr/0001-linguagem-python.md` para o registro da decisão.
