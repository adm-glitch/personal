# Decisions — what was chosen, why, and what was rejected

Every decision here is settled unless `04-open-questions.md` says otherwise.

## Data model

**Five levels: bairro → quadra → face → endereço → domicílio.**

- **Endereço is always a container**, even when it holds exactly one home. Discovering
  that nº 4310 is a 12-flat building is then adding 11 siblings, never a type conversion.
- **`COD_UNICO_ENDERECO` is the key.** Never street+número — 10% of those repeat across
  quadras, and 41% of Vigia's doors have no number at all.
- **Quadra identity is `(setor, número)`.** "Guamá quadra 001" names **95 different
  blocks** — bairro+número is ambiguous for 90% of quadras. Rejected.
- **Quadra display label = the two bounding street names** ("Canaa × Bom Jesus", 76%
  unique) plus a campaign code (`TF-24`) assigned geographically per bairro.
  Freeze the codes at campaign start; regenerating renumbers them.
- **`face_id` is derived and nullable**, not primary — the CNEFE↔faces join is 85.6%.

## Statuses

`contato · ausente · recusou · inexistente · não localizado` plus bulk-only
`não autorizado · inacessível · fechado`.

Two distinct roll-ups, deliberately:

- **VISITADO** = any recorded status. Paints the map — somebody physically went.
- **RESOLVIDO** = the denominator can close on it (contato, recusou, inexistente, and the
  three bulk states). *Ausente* and *não localizado* stay pending.

`inexistente` (shrinks the denominator) and `não localizado` (admits a gap) must never be
merged. That is how coverage numbers start lying.

## The interface

**The table is primary; the map is confirmation.** Non-negotiable, because 14% of Belém
households (29% in Vigia) sit on a kerb with no line — map-first would make them
unreachable. Also because 5 of quadra 001's 13 faces have ≤3 homes: nobody finds a 5-metre
kerb with a fingertip, so every face is a list row.

- Selecting on the map **navigates the table without opening or closing it**.
- **Working context ≠ browsing context.** `workQ/workF` (where you say you are) is
  separate from `curQ/curF` (what you're looking at); browsing elsewhere shows a
  "só olhando" pill. Otherwise revisits get mistaken for coverage.
- Actions render **inline directly beneath the tapped row**.
- Bulk status is behind a **swipe right** (⋯ button for keyboard) — the exception path,
  deliberately not a tap. **Log every bulk action** with actor, count and reason: one
  swipe can resolve 83 doors and there is no supervisor in the loop.
- Map labels strictly by zoom: bairros → quadra codes → street names → house numbers.
  Selecting a quadra highlights it and nothing more.

## Location and battery

- **A PWA cannot do background geolocation.** No API. Don't design around tracking.
- **The screen is the bigger drain, not the GPS.** The kerb list means the phone goes in
  the pocket between doors — that saves more than any GPS tuning.
- Coarse `watchPosition` baseline; high-accuracy bursts only while a face is open;
  manual "onde estou" button. Never continuous high accuracy.
- **Offline reverse geocoding** — nearest kerb-face from the shipped geometry, no network.
- **Imprecise GPS is the normal case in passagens/vilas** (0.01 representation ratio).
  So the app *asks* — "Em qual rua você está?" with the three nearest as buttons — rather
  than showing a wrong answer confidently.
- **A manual pin survives GPS recovery.** GPS then *offers* ("GPS: Passagem X"), never
  imposes. "Trocar local" is available in every signal state.
- Estimates only, unverified on real handsets: GPS 3–7%/h by mode, screen ~16%/h,
  ~50% for a 4-hour shift on high accuracy.

## Offline map delivery

**Bake the whole municipality into the install** (A), plus a silent versioned manifest
check when online (B). No sync button.

Rejected: lazy per-bairro (breaks on reassignment while offline); tile pyramid + MapLibre
(bigger, more RAM, flaky WebGL on cheap Androids, and you'd still ship the address data
separately).

- Payload is **one gzipped binary** decoded into **typed arrays**. 528,686 households
  cannot live in JS objects. Numbers and complementos stay as raw bytes with offsets,
  decoded only when displayed.
- **Canvas 2D, not MapLibre.** MapLibre sits at 150–250 MB resident; the target is basic
  Androids. Cost is ~500 lines of pan/zoom/pick — covered by the harness.
- Visits out: append-only IndexedDB queue, client UUID, idempotent server upsert.
  Coverage in: per-face count deltas (~94 KB for a 75-person day).

## Routing and targeting

**Do not build route optimisation.** The `CD_FACE` circuit is a proven full-coverage route
(84% consistent) and beating it saves 19% — noise against 10× density variation.

**Build targeting instead.** Density per 100 m of kerb; 25% of households from 6% of the
kerb; passagens and vilas are the densest. That is the "Onde ir agora" panel.

## LGPD

**Political opinion is sensitive data** (Art. 5º II). Art. 12 §2º makes inferred/profile
data personal data — a canvasser's *impression* is not a loophole. Art. 11 requires
specific, highlighted consent; legitimate interest is unavailable.

**The split, decided:**

- **Contact outcome per address** — operational, defensible, needed to avoid re-knocking.
  Keep the vocabulary operational ("recusou-se a falar", never "hostile to the candidate").
- **Sentiment as an increment-only counter on the quadra**, no foreign key to any address,
  suppressed below ~10 residences.

Aggregating sentiment at **face** level was rejected: 64.5% of faces have <10 residences,
so it re-identifies. Quadra median is 34; only 15.6% fall under 10.

Also: the app is a campaign expense for *prestação de contas*; TSE Res. 23.610/2019 as
amended by 23.732/2024 applies.

## Colour

Validated with the dataviz validator, not chosen by eye.

- House states use **hue *and* shape** — red/green fails deuteranopia at ΔE 4.1, and ~4–5
  of a 75-person team will be red-green colourblind.
- Coverage magnitude: **single-hue blue sequential ramp**.
- The admin choropleth's "situação dominante" has **exactly three classes** — no
  five-hue categorical palette passes all-pairs CVD separation on a choropleth.
- Status colour never carries meaning alone; counts (`3/9`) always accompany it.
