# app-map-reachout — canvassing coverage app for Belém/PA

Read this first. It is the handoff from the design session; the detail lives in `docs/`.

## What this is

A field app for a **community outreach team doing door-to-door visits in Belém**, plus a
coordinator dashboard. Canvassers record what happened at each door; the map paints
coverage. Built on free IBGE census data — no proprietary basemap, no tile server.

**It is an election campaign.** First round **4 Oct 2026**; propaganda started 16 Aug 2026.
That deadline drives every scope decision. See `docs/04-open-questions.md`.

## The one-paragraph architecture

Ship the whole municipality as **one gzipped binary** (Belém: 3.7 MB; Vigia: 211 KB),
decode into **typed arrays** in the browser, render with **Canvas 2D**. Hierarchy is
**bairro → quadra → face → endereço → domicílio**. The *table* is the primary interface
and the map is confirmation, because 14% of Belém households sit on a kerb IBGE never drew.
Work is keyed on IBGE's `COD_UNICO_ENDERECO`, never on street+number.

## Repo layout

| path | what |
|---|---|
| `docs/01-data-sources.md` | every dataset, verified URL, what it contains |
| `docs/02-findings.md` | **every measured number** — do not re-derive these |
| `docs/03-decisions.md` | design decisions, rationale, and what was rejected |
| `docs/04-open-questions.md` | what is still undecided |
| `pipeline/gen_muni.py` | builds field + admin payloads for **any of the 5,570 municipalities** |
| `mockups/parts/` | the four source fragments the field app is assembled from |
| `mockups/build_muni.py` | assembles a field-app HTML from parts + payload |
| `mockups/harness/` | headless test harnesses (node, no browser) |
| `data/` | generated payloads; source downloads are **not** committed, re-fetch them |

## Working agreements established in the session

- **Verify, don't assume.** Every number in `docs/02-findings.md` was measured from the
  actual data. Several early estimates were wrong and were corrected — read the
  "corrections" section before quoting anything.
- **Run the harness before publishing.** `mockups/harness/ch.mjs` executes the real
  decoder and UI against the real payload with stubbed DOM. It has caught: a duplicate
  DOM id, a zero-size canvas boot failure, a DPR-stale ghosting bug, and a crash on
  faces with no geometry.
- **Build checks are part of the build.** `build_muni.py` fails on duplicate ids, missing
  `getElementById` targets, `getContext` on a non-canvas, external URLs (CSP), and
  undefined CSS custom properties.
- **Colour is validated, not chosen by eye.** Categorical palettes were run through the
  dataviz validator. A five-status choropleth fails CVD separation — that is why the
  admin panel's "situação dominante" has exactly three classes.

## Rebuilding

**Start here — one command proves the pipeline is intact:**

```bash
bash verify.sh            # Vigia only, ~5 s
bash verify.sh --full     # + Belém, ~40 s
```

It regenerates payloads from source, rebuilds all four artifacts, and runs both harnesses.
If it prints `OK`, everything works.

For one municipality by hand (any of the 5,570 — the UF is derived from the code):

```bash
bash pipeline/fetch.sh 1501402                     # ~1.5 GB of IBGE + OSM source data
python3 pipeline/gen_muni.py 1501402 "Belém" cnefe_1501402.json.zip roads_1501402.json belem
python3 mockups/build_muni.py  data/belem "Belém" "71 bairros" belem_app.html "<lede>" "<eyebrow>"
python3 mockups/build_admin.py data/belem.admin.json belem_admin.html
```

Every script resolves paths against the repo root, so run them from anywhere.
Source data lives in `data/` and is gitignored; only generated payloads are kept.

> `gen_muni.py`'s campaign simulation is **uniform random**. The Belém admin panel that was
> published during the design session used `pipeline/gen_admin.py`, which has a hand-tuned
> per-bairro priority table and produces a more realistic-looking picture. Both are fake —
> the shape is the deliverable, not the values.

## The thing that is still blocking

**Hosting / backend has never been chosen.** Everything so far is client-side mockups
against real data. No API, no database, no auth. That is the next decision, and nothing
in `docs/03-decisions.md` depends on it — the payload format and the UI are settled.
