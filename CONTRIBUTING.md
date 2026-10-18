# Contribuindo com o EDP

Obrigado pelo interesse! Este é um projeto pequeno e **sem dependências de
runtime**: todo o código é Python puro (biblioteca padrão) e roda em macOS,
Linux e Windows a partir do mesmo fonte.

## Antes de abrir uma issue

Muitos problemas de boot **não são do EDP, e sim da gravação**. Antes de
reportar, confira:

- a mídia é **boa** e foi gravada a **4x**, **finalizada** e **verificada**?
- o console está em **English**?
- o modelo é compatível com o boot direto? (Slim: qualquer; Phat: 2.10/2.12/3.04)
- no modo clássico, o **loader ESR está instalado** no console?

Detalhes no [FAQ do README](README.pt-BR.md#faq-e-limitações) e na seção
[Gravar o disco](README.pt-BR.md#gravar-o-disco).

## Ambiente de desenvolvimento

```bash
git clone git@github.com:Dougwan/ESR-Disc-Patcher.git
cd ESR-Disc-Patcher

# CLI/GUI direto do fonte (sem instalar nada)
PYTHONPATH=src python3 -m edp --help
PYTHONPATH=src python3 run-gui.py
```

## Rodando os testes

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -t . -v   # 91 testes
```

Todo PR deve manter a suíte **verde** e, se mudar comportamento, **adicionar ou
ajustar testes**. Não existe etapa de build.

## Estilo e convenções

- **Python 3.9+**, somente biblioteca padrão — nada de dependências novas de
  runtime sem discussão prévia.
- Mensagens, docstrings e comentários em **português**; identificadores em
  inglês.
- Camadas: `domain` → `iso` → `patcher` → `cli`/`gui`. A dependência **aponta
  sempre para baixo**; a GUI e a CLI só falam com o `EsrService`.
- Preserve o **contrato público** (`EsrService`, `IsoAnalysis`, `FdvdbReport`,
  `EsrError`, `edp.paths.default_output_path`).
- **Nunca** altere a ISO de origem por padrão — a saída é sempre um arquivo novo.

## Commits

Commits **atômicos**, com mensagens no formato
[Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`,
`docs:`, `test:`, `refactor:`, `build:`.

## Licença

Ao contribuir, você concorda em licenciar sua contribuição sob a
**GPL-3.0-or-later** (ver [`LICENSE`](LICENSE)).
