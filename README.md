# app-map-reachout

Door-to-door canvassing coverage app for **Belém/PA**, built entirely on free IBGE census
data — every address in the city as a GPS point, with no proprietary basemap, no tile
server and no municipal contact required.

**528.686 households · 8.604 quadras · 71 bairros · one 3,7 MB offline binary.**

Verified to work for any of Brazil's 5.570 municipalities: the same pipeline builds
Vigia/PA — a small town with no IBGE bairro mesh — into a 211 KB payload.

## Start here

**[`CLAUDE.md`](CLAUDE.md)** — the handoff: architecture in a paragraph, repo layout,
working agreements, rebuild commands.

| doc | what |
|---|---|
| [`docs/01-data-sources.md`](docs/01-data-sources.md) | every dataset, verified URL, what's in it |
| [`docs/02-findings.md`](docs/02-findings.md) | **every measured number** — and the corrections |
| [`docs/03-decisions.md`](docs/03-decisions.md) | what was chosen, why, what was rejected |
| [`docs/04-open-questions.md`](docs/04-open-questions.md) | what's still undecided |
| [`docs/05-artifacts.md`](docs/05-artifacts.md) | the five published interactive mockups |

## Prove it still works

```bash
bash verify.sh --full
```

Regenerates payloads from source, rebuilds all four artifacts, runs both headless
harnesses. Belém takes ~9 s.

## Status

Design and mockups complete against real data. **No backend has been chosen yet** — see
`docs/04-open-questions.md`. Nothing client-side depends on that decision.
