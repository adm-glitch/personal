# Open questions

## Blocking

### 1. Hosting / backend — never chosen
Asked repeatedly across the session, never answered. **Nothing else is blocked on it** —
the payload format, hierarchy, statuses and UI are all settled and none of them depend on
the choice. But no API, database or auth exists.

Default if the answer is "you pick": **Postgres + PostGIS behind a thin API**. It fits the
model (append-only visit log, per-face counters, quadra-level sentiment counters) and the
timeline.

Sub-decisions that come with it:
- auth for 75 canvassers — invite code or magic link, not passwords
- how the outbound queue authenticates offline-then-online
- who can read individual records vs aggregates only (LGPD, see `03-decisions.md`)

## Decided by the user, recorded here so they are not re-litigated

- **Sweep, not target list.** CNEFE points *are* the worklist.
- **Offline required, both directions.** Map available with no data plan; visits recorded
  offline; no sync button.
- **No institutional access** to CODEM or SEFIN — public data only.
- **50–75 canvassers**, free-for-all assignment with **regional managers** cutting turf.
- **Quadra-level sentiment**, never per household.
- Claude builds it end-to-end with the user's guidance.

## Needs a decision before build

### 2. Pairs or solo
Canvassing in pairs is the safety standard in every field-organising guide, and matters in
peripheral Belém. It halves effective capacity (~34% → ~17% of the city) unless a pair
splits opposite sides of the same passagem. Changes turf sizes. **Not yet decided.**

### 3. The `s/n` problem for small municipalities
41.4% of Vigia's doors have no number. The doorstep flow assumes "tap the pin labelled
nº 74". Needs a different affordance — position along the kerb ("3ª casa depois da
esquina"), a photo, or a canvasser-supplied name. **Belém at 8.3% is workable; Vigia is not.**

### 3b. Naming faces so a canvasser can pick one
Grouping faces by street name was measured and **does not simplify anything** — 1.30×
collapse in Belém, 1.16× in Vigia, four rows becoming three (`02-findings.md`). So the
face list stays, but `CD_FACE` must not be what the canvasser reads. Proposed and **not
yet built**: label every row `Passagem São Jorge — lado ímpar · 12 casas`, drop the face
number from the UI while keeping it as the key, and for the 10.8% of quadras with no
geometry let the address list itself be the face. Needs a design pass.

### 4. Duplicate-flag rule
The mockup ships `<50 m` (13,490 households). The analysis says **same setor & <20 m**
(3,344, 0.63%) is the reviewable set. Changing it means regenerating the payload —
do it as part of the real build.

### 5. Campaign quadra codes
`TF-24` style codes are derived geographically. **Freeze them once at campaign start** —
regenerating mid-flight renumbers blocks that people are naming out loud.

### 6. Battery figures are estimates
GPS 3–7%/h, screen ~16%/h, ~50% per 4-hour shift. **Never measured on the team's actual
handsets.** Do that before promising anything.

## Known risks

- **Bulk marking is the most abusable control.** One swipe resolves 83 doors, free-for-all
  assignment means no supervisor in the loop. Mitigation designed (audit queue in the
  dashboard) but not built.
- **Timeline.** First round 4 Oct 2026; propaganda started 16 Aug 2026. Every week of
  build is ~2% of the city not walked.
- **ODbL.** The OSM street layer requires attribution and carries derived-database
  obligations. Don't ship it unattributed in a campaign app.
- **The visit data in both admin mockups is simulated.** Shape is real, values are not.
