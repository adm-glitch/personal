# Published artifacts

Five interactive pages published during the design session (13–14 Aug 2026). They are
**private to Mauricio's claude.ai account** until shared from each page's share menu.

All of them are rebuildable from this repo — see `CLAUDE.md`. The links are recorded
because they carry the *published* state, including the hand-tuned Belém campaign
simulation that `pipeline/gen_muni.py` does not reproduce (see the note in `CLAUDE.md`).

| # | page | what it shows | rebuild |
|---|---|---|---|
| 1 | [Belém — research prototype](https://claude.ai/code/artifact/2dc83f71-48b1-43f2-88d0-63c427536c42) | The original evidence page: Terra Firme map from real IBGE data, coverage painting, the satellite-alignment demo, and *one block three ways* on the Bom Jesus quadra | not scripted — superseded by the field app |
| 2 | [Belém — app de campo](https://claude.ai/code/artifact/d61c3d37-6a95-412d-880e-93ef7d32d5bf) | The whole city in the browser: 528.686 domicílios, 8.604 quadras, 71 bairros from a 3,7 MB binary. Field app with GPS states, bulk actions, data-gap flags | `build_muni.py` |
| 3 | [Belém — painel de cobertura](https://claude.ai/code/artifact/9b130c77-ce5a-4840-8ca2-c4fad4a238cc) | Coordinator dashboard: choropleth by bairro/quadra, status filters, targeting list, audit queue | `build_admin.py` |
| 4 | [Vigia — app de campo](https://claude.ai/code/artifact/f1a4f59e-6b9d-4503-97fd-e35edce5efee) | Same code on a small municipality with **no IBGE bairro mesh** — the portability test | `build_muni.py` |
| 5 | [Mutirão Vigia — painel de cobertura](https://claude.ai/code/artifact/e704fd79-4b92-448c-98bc-465f0ecfc7d4) | Admin panel adapted to a municipality with no bairro polygons | `build_admin.py` |

## Caveats

- **Visit data in 3 and 5 is simulated.** The geometry and household counts are real IBGE;
  the coverage numbers are not. Read the shape, not the values.
- Page 1 predates the binary payload format and the five-level hierarchy. It is kept for
  the research it documents — the GeoPDF inspection, the alignment demo, the vila analysis —
  not as a design reference.
- Updating a page means republishing to the **same URL** from a session that has it, or
  passing the URL explicitly. Publishing without it creates a duplicate.
