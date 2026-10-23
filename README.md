# Observatório do gasto público de Belém/PA

Fase **exploratória** e **privada**. Objetivo: controle social e estruturação da informação sobre como a Prefeitura de Belém
gasta o dinheiro e com quem — tornar o gasto legível, sem acusar ninguém.

- Escopo: município de Belém (direta, indireta, fundos, Câmara) · 2026 (execução + contratos vigentes) · sem marca · COP30 fora.
- Ponto de partida: [`docs/handoff-2026-10-23.md`](docs/handoff-2026-10-23.md) (pesquisa da primeira sessão; nada testado ao vivo).
- Próximo passo: **Fase 0** — confirmar cada fonte e escrever `fontes/fontes.md` (inventário testado).

## Estrutura
- `docs/` — handoff, método, decisões
- `fontes/` — inventário testado das fontes (Fase 0)
- `raw/` — respostas originais de cada coleta (JSON/HTML/PDF) com data; não versionar arquivos grandes
- `scripts/` — coletores (Python: httpx, playwright, pdfplumber); banco em DuckDB
