# Findings — every number measured, not estimated

Do not re-derive these. Each was computed from the actual downloaded data.
Where an earlier figure was wrong, the correction is recorded rather than quietly replaced.

## Belém, the base numbers

| | |
|---|---|
| Addresses in CNEFE | 618,089 |
| **Private households** (`COD_ESPECIE=1`) | **528,686** |
| Field-captured GPS (`NV_GEO_COORD=1`) | 564,624 (**91.3%**) |
| Addresses with no house number | 51,190 (**8.3%**) — vs 22.8% nationally |
| Named block-faces | 38,718 |
| Quadras | 7,726 (8,604 once address-only ones are included) |
| Setores | 1,809 |
| Official bairros | 72 |
| OSM street ways | 27,476 (5,905 names, 56% named) |

**Offline payload, whole city, gzipped: 3.7 MB.** Households 2.3 MB, faces 1.3 MB,
streets 0.46 MB, water/coast 47 KB, bairro outlines ~100 KB.

## Coverage geometry — the gaps

| gap | count | share |
|---|---|---|
| Households on a face with **no line in the base** | 75,813 | **14.3%** |
| Households in a quadra with **no outline at all** | 41,565 | 7.9% |
| Quadras with no geometry | 878 of 8,098 | 10.8% |
| Census lines carrying no quadra/face attributes | 9,441 | — |

**Wildly uneven, and it tracks informality.** Worst: Maracacuera 53.6%, Campina 35.6%,
São Clemente 34.7%, Pratinha 34.6%, Águas Lindas 32.9%, Tapanã 29.4%.
Best: Jurunas 0.3%, Batista Campos 0.6%, Sacramenta 2.1%, Umarizal 2.2%.

> A 6-bairro window around Terra Firme showed 23%. That was a **local peak**, not the
> city figure. Citywide is 14.3%.

## Duplicate street numbers

Of 276,834 distinct numbered rua+número pairs, **27,759 (10.0%)** appear in more than one quadra.

| | count | share **of what** |
|---|---|---|
| >50 m apart — two streets sharing a name | 24,327 | 88% of the 27,759 |
| **<50 m apart — real ambiguity** | **3,432** | 12% of the 27,759 |
| Households on one of those close pairs | 19,219 | **3.6% of 528,686 households** |
| Entrances with no number at all | 8,685 | 2.6% of entrances |

> Those two percentages have **different denominators**. An earlier table put them in one
> "share" column and they looked contradictory. Always name the base.

**Separation histogram** (median 585 m, p10 41 m, p25 116 m):

| distance | pairs | same setor |
|---|---|---|
| 0–5 m | 269 | 64% |
| 5–10 m | 400 | **67%** |
| 10–20 m | 756 | 62% |
| 20–50 m | 2,007 | 62% |
| 50–100 m | 2,766 | 57% |
| 100–200 m | 3,675 | 50% |
| 200–500 m | 3,501 | 20% |
| 500 m–2 km | 4,294 | 2% |
| **2 km+** | **10,091 (36%)** | **0%** |

**There is no valley — the discriminator is "same setor", not distance.** It falls from
67% below 10 m to 0% past 2 km.

**GPS cannot explain a 70 m gap.** 99% of these records are field GPS (±5–10 m), so two
readings of one door land within ~20 m. The band GPS error explains is **0–20 m: 1,625
pairs**, 64% same-setor.

Candidate flag rules:

| rule | households flagged | share |
|---|---|---|
| <50 m (what the mockup ships) | 13,490 | 2.55% |
| <30 m | 7,465 | 1.41% |
| <20 m | 5,019 | 0.95% |
| **same setor & <20 m — recommended** | **3,344** | **0.63%** |

**A failed test worth keeping:** matching `COMPLEMENTO` does **not** identify duplicates.
The "same complemento" rate is 55–65% in *every* distance band including 2 km+ — it is just
the base rate of blank complementos. Any dedup built on that field would be quietly wrong.

## The census walking route

Verified empirically over 5,876 quadras with 4+ faces:

- **84.1%** have `CD_FACE` numbered as a consistent **clockwise circuit** around the block
- **83.5%** have consecutive faces sharing an endpoint — a physically walkable chain
- The 14.7% that break the circuit are enriched **3.4×** for *vilas* and *becos*
  (28.6% vs 8.5%) — interior corridors interrupt the perimeter

**A proven full-coverage route already exists in the free data.** Do not design one.

### Route optimisation is not worth building

Terra Firme, 19,328 homes, 100 km of kerb. Connector distance is straight-line, so all
three are optimistic; the comparison is what matters.

| order | walk | connectors | m/home |
|---|---|---|---|
| A census circuit, quadras by number | 137.9 km | 27.4% | 7.1 |
| B census circuit, quadras by geography | 137.8 km | 27.4% | 7.1 |
| C every face freely reordered | 111.1 km | 10.0% | 5.7 |

**A→B saves 0.0%.** B→C saves 19%, and all of it is "cross the alley instead of circling
the block". Against door density that varies **10×** between faces, 19% is noise.

> Two earlier versions of this were wrong: first I sorted by `CD_FACE` across a whole
> setor (numbering restarts per quadra), then I forced forward traversal (face geometry is
> digitised in arbitrary direction). Both inflated the saving to 53%. The fair baseline
> chooses direction greedily.

## Targeting beats routing

Door density per 100 m of kerb: median **10.6**, top decile **27+**, bottom decile **<2.8**.

**Walking the densest kerb first reaches 25% of all households from 6% of the kerb**
(201 km of 3,351 km). Half the city from 20%.

| street type | faces | median doors/100 m |
|---|---|---|
| **Passagem** | 8,260 | **14.1** |
| **Vila** | 1,854 | **13.2** |
| Travessa | 4,625 | 11.0 |
| Rua | 9,459 | 9.4 |
| Avenida | 2,602 | 9.2 |
| Rodovia | 430 | 5.1 |

The densest kerb is the informal kerb. Operational and political optima coincide.

## GPS reliability by street type

11,654 recorded enumerator trace vertices, matched to kerbs (median 4.0 m when matched):

| type | % of kerb | % of GPS fixes | ratio |
|---|---|---|---|
| Estrada | 2.0% | 14.6% | **7.12** |
| Rua | 32.6% | 44.1% | 1.35 |
| **Passagem** | 22.5% | 8.1% | **0.36** |
| **Travessa** | 14.3% | 3.2% | **0.23** |
| **Vila** | 3.2% | 0.0% | **0.01** |

**The census's own GPS effectively failed inside the vilas.** Holds within short traces
too (<200 m, i.e. actually working: RUA 47%, PASSAGEM 10%, VILA 0%), so it is not a
travel artefact. Imprecise GPS is the *normal* case in the dense passagens.

## OSM building footprints — do not ship as primary

148,026 in Belém, 27% of households, **inversely correlated with need**:

| bairro | households | OSM buildings | ratio |
|---|---|---|---|
| Marco | 23,851 | 20,369 | 0.85 |
| Guamá | 29,452 | 22,572 | 0.77 |
| Tapanã | 26,929 | 315 | **0.01** |
| **Terra Firme** | 16,086 | **0** | **0.00** |

Blank exactly where a community operation works. Reads as "app is broken", not "no data".

## Vigia/PA — the portability test

IBGE code **1508209** (1508100 is Tucuruí — an early mistake, caught).

| | Belém | Vigia |
|---|---|---|
| Households | 528,686 | 19,254 |
| **Bairro mesh** | 72 polygons | **none** |
| **Sem número** | 8.3% | **41.4%** |
| Households on a lineless face | 14.3% | **29.1%** |
| Quadras with no outline | 10.8% | 13.7% |
| OSM streets named | 56% | **14%** |
| Complemento present | 45.1% | 15.4% |
| Field GPS | 91.3% | **99.8%** |
| Payload gzipped | 3.7 MB | **211 KB** |

**Only 25 of Pará's 144 municipalities have a bairro mesh.** Fallback: `distritos`
(national) + `DSC_LOCALIDADE` (117 raw → 55 per-quadra for Vigia). Localidade has **no
polygon**, so the coarse choropleth must colour quadras instead of bairro shapes.

**41.4% of Vigia's doors have no number** — five times Belém. The "tap the pin labelled
nº 74" flow degrades badly and needs a different affordance for small municipalities.
This is not fixable with better GPS: Vigia's GPS is *better*.

## Team capacity (the constraint nobody can engineer around)

Canvassing rates from field-organising literature: 25+ doors/hour dense urban, 15–20
suburban; turfs of 40–60 doors per 2–3 h shift; 1–3 min/door; best hours 16:00–19:00.
ACS/health model: microárea ≤750 people, min 8 visits/day, 95% monthly coverage target.

75 canvassers, 16 Aug → 4 Oct:

| pace | h/day | days | doors | share of Belém |
|---|---|---|---|---|
| 15/h | 3 | 30 | 101,250 | 19% |
| **20/h** | **4** | **30** | **180,000** | **34%** |
| 25/h | 4 | 40 | 300,000 | 57% |

**Realistically about a third of the city.** This is a prioritisation tool, not a
completion tool. Canvassing in pairs (standard for safety) halves it again.

## Rendering performance (measured, Node + stubbed canvas)

- Whole-city decode: **540 ms**, ready at **640 ms**
- Full extent: **4,603 strokes/frame**; zoomed in: **83** — 98% cut from bbox culling
- Vigia: 46 → 6 strokes/frame
- Below 1.4× zoom, skipping 8,604 quadra hull fills is what makes the bairro view viable
