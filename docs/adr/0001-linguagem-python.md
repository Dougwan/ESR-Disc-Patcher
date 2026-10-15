# ADR-0001 — Linguagem: Python 3 com biblioteca padrão

- **Status:** Aceito
- **Data:** 2026-10-14
- **Contexto:** ferramenta desktop para aplicar patch ESR em ISOs de PS2.

## Decisão

Implementar em **Python 3.9+** usando **apenas a biblioteca padrão**.

## Justificativa

- O domínio é E/S de bloco + aritmética de bytes + parsing simples; o gargalo é
  disco, não CPU. Não há ganho relevante de Rust/Go.
- Iteração e refatoração rápidas; testes com `unittest` (stdlib); GUI nativa com
  `tkinter` (stdlib), eliminando dependências de instalação.
- Zero dependências de runtime ⇒ distribuição e reprodução triviais.

## Alternativas consideradas

- **Rust:** binário único, mas iteração lenta e GUI desktop fraca; a segurança
  de memória protege contra pouco neste código banal. Rejeitado.
- **Go:** bom para binários/concorrência, mas manipulação binária verbosa e GUI
  imatura. Rejeitado.

## Consequências

- Requer interpretador Python instalado (disponível em macOS/Linux/Windows).
- Se um dia for necessário um binário único, `PyInstaller` ou uma reescrita
  pontual do core em Rust (que é puro e testável) ficam viáveis sem reescrita
  da arquitetura.
