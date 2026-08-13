# MarketScan — Implementation Plan

**Brazilian grocery receipt scanner (NFC-e), iOS MVP — Pará only.**

| | |
|---|---|
| Status | Planning complete, M0 not started |
| Last updated | 2026-08-13 |
| Scope | NFC-e receipts issued in Pará (UF code 15). Other states explicitly out of scope. |
| Success criterion | Given a real NFC-e QR code from a Belém supermarket, reliably retrieve and parse the purchased items into structured data. Not "the app looks good." |

This document is the shared reference across the Windows/Cloud checkout and the
Mac/Xcode checkout. Update it as findings land — especially §5, which is
currently full of hypotheses that real receipts will confirm or kill.

---

## 1. Guiding principles

Carried over from the project brief, restated here because they constrain
almost every decision below.

1. **investigate → prove → model → implement.** Not: design the whole platform,
   then discover the assumptions were wrong.
2. **Never discard raw fiscal data.** Normalization is a separate layer built on
   top of preserved raw item rows. If normalization is wrong today and better
   tomorrow, the original data must still be there to re-derive from.
3. **Pará only, but isolate Pará.** No adapters for the other 26 UFs. Also no
   Pará-specific assumptions leaking into the core purchase model.
4. **No speculative architecture. No dependencies without a demonstrated
   problem.** Native Apple APIs where practical.
5. **Receipt ingestion comes first.** Product normalization is deliberately
   unsolved in the first implementation.

---

## 2. Environment assessment (2026-08-13)

### Repository

Started effectively empty: one commit, a one-line `README.md`, and a stock
GitHub Swift/Xcode `.gitignore`. Nothing to preserve.

### The Cloud Code session is Linux, not Windows

Development happens from Windows, but Claude Code on the web runs in an
**Ubuntu 24.04 x86_64** container. This is better than Windows would be:
whatever we can test in a session runs in CI too.

Present: Python 3.11, Node 22, curl, git.
**Absent: any Swift toolchain.**

### Network egress is an allowlist, and it blocks what we need

All outbound HTTPS passes through a policy-enforcing proxy. The cloud
environment sits at the **Trusted** access level, which covers package
registries, GitHub, and cloud SDKs — and nothing else.

Probed on 2026-08-13:

| Host | Result | Consequence |
|---|---|---|
| `www.sefa.pa.gov.br` | 403 CONNECT denied | No live NFC-e recon |
| `appnfc.sefa.pa.gov.br` | 403 CONNECT denied | ″ (host is a guess — see §5) |
| `www.nfe.fazenda.gov.br` | 403 CONNECT denied | No national-portal fallback |
| `download.swift.org` | 403 CONNECT denied | **Cannot install Swift → cannot compile or test any Swift we write** |
| `github.com`, `api.github.com` | OK | Git workflow fine |
| `swift.org` | OK | Docs only, not downloads |

**Resolution — required before M1/M2.** In the environment selector at
claude.ai/code (cloud icon above the message box → gear icon), set
**Network access** to **Custom** and add:

```
sefa.pa.gov.br
*.sefa.pa.gov.br
download.swift.org
```

Then **check "Also include default list of common package managers"** —
unchecked *replaces* the Trusted list rather than extending it, which would
break npm, PyPI, and `raw.githubusercontent.com`.

Notes:

- Running sessions do not re-read environment config. **Start a new session**
  after saving; the current one keeps its old policy.
- GitHub traffic uses a separate credential proxy, independent of this setting.
  A wrong allowlist cannot break push/pull.
- The allowlist is per-environment and personal to the account. There is no
  org-level allowlist.
- Once Swift installs, move the install into the environment's **setup script**
  so it is cached (~7 days) and future sessions start with the toolchain ready.
- `appnfc.sefa.pa.gov.br` is a guess. Confirm the real host from an actual QR
  URL before finalizing the allowlist (§5, §9).

---

## 3. Architecture decisions

Each decision records the trade-off accepted, per the brief's request.

### D1 — Core logic is a local SwiftPM package; the app target is a thin shell

```
Packages/MarketScanCore/   ~90% of the code, no Apple-UI dependencies
App/MarketScan.xcodeproj   thin shell, depends on the local package
```

**Why.** This solves the Windows/Xcode problem structurally rather than with
tooling. `project.pbxproj` cannot reasonably be authored off a Mac and merges
badly. If new files land in the *package* instead of the *app target*, the
pbxproj almost never changes — so it is created once on the Mac and then left
alone. Bonus: `swift test` runs on Linux.

**Trade-off.** Explicit `public` on the API surface and `import MarketScanCore`
in app code. Cheap.

**Rejected.** XcodeGen/Tuist — a dependency solving a problem this structure
already solves. Hand-editing pbxproj from Windows — miserable. Xcode 16+
synchronized folder groups are a reasonable extra safety net for the app
target, not a replacement for this split.

### D2 — Core performs no networking; it takes an injected `HTTPClient`

**Why.** Tests run against committed fixtures, never live SEFAZ: deterministic,
offline, fast, and no dependence on Linux `FoundationNetworking` quirks. Real
`URLSession` lives in the app layer.

**Trade-off.** One protocol plus one fake. Negligible.

### D3 — Domain types are plain structs; SwiftData `@Model` classes live in the app and map to them

**Why.** SwiftData is Apple-only. If domain objects *are* `@Model`, then
deduplication, aggregation, and unit conversion all become Mac-only to test —
exactly what the brief's Windows-compatibility requirement asks us to avoid.
The repository *protocol* lives in Core; SwiftData implements it in the app.

**Trade-off.** Mechanical mapping between `Receipt` (struct) and
`ReceiptEntity` (`@Model`). Keep it thin and boring.

**Rejected.** `@Model` as the domain type — simpler, but drags Apple frameworks
into Core and kills Linux testing.

### D4 — The retrieval transport is deliberately undecided

Resolving this *is* the proof-of-concept. See §5 for the decision tree. We do
not pick a transport before seeing real responses.

### D5 — Provider abstraction, one implementation

`NFCeProvider` protocol in Core, `ParaNFCeProvider` as the only conformance.
Enough to keep Pará parsing assumptions from contaminating the purchase model,
without building 26 adapters nobody has data for.

---

## 4. What is stable spec vs. what must be verified

**Safe to implement now** — the 44-digit NFC-e access key layout and its mod-11
check digit. Long-stable, and it yields real data with no network at all:

```
cUF(2) AAMM(4) CNPJ(14) mod(2) série(3) nNF(9) tpEmis(1) cNF(8) cDV(1)   = 44
```

For this project: `cUF = 15` (Pará), `mod = 65` (NFC-e). From the key alone we
get issuer CNPJ, emission year/month, document number, series, and whether the
receipt was issued in contingency (`tpEmis`).

**Must be verified against real receipts — do not assume:** the exact
pipe-delimited layout of the QR code's `p=` parameter. The field set differs
between normal online emission and offline/contingency emission, and the
governing National Technical Note has been revised more than once. Read this
off actual Belém receipts, not off recollection.

---

## 5. Pará NFC-e proof-of-concept design

### Questions the PoC must answer

**Transport**
- What exactly is in the QR payload? Which host does it point at? Which QR
  version(s) appear on current Belém receipts?
- Does a plain anonymous GET return the full receipt?
- Cookies, session state, JSF `ViewState`, redirects, JavaScript, CAPTCHA?
- Is the response HTML, XML, JSON, or something else?
- Rate limiting? Any behaviour that punishes repeated lookups?

**Receipt fields available**
access key · issuer name · CNPJ · date/time · total · document number · original QR URL

**Item fields available**
raw description · quantity · commercial unit · unit price · total price
Then investigate: GTIN/EAN · NCM · product/item code · per-item discounts

### Transport decision tree, in preference order

| Path | Condition | Implementation |
|---|---|---|
| **A** | Plain anonymous GET returns complete HTML | `URLSession` + parser. Clean, ideal. |
| **B** | Needs session cookies / `ViewState` / redirect chain | `URLSession` + cookie jar. Fragile but workable. |
| **C** | Needs JavaScript, or presents a CAPTCHA | `WKWebView` on-device, extract DOM via JS. Ugly, but stays local-first with no backend. A user-visible WebView lets the user solve a CAPTCHA themselves. |
| **D** | Effectively closed | Fall back to manual key entry, or reconsider the data source. |

The `.seam` extension seen on Pará's consultation endpoint suggests JBoss
Seam/JSF, which raises the odds of B or C. **But:** a CAPTCHA on the *manual
key-entry form* does not imply one on the *QR-URL path* — the QR's hash
parameter typically authenticates that request. Settling that distinction is
one of the first jobs of the PoC.

Explicitly per the brief: **do not assume the full NFC-e XML is anonymously
downloadable** just because an XML exists behind the fiscal document. The
public consumer consultation reached through the QR code is our first source.

### Fixture diversity to collect deliberately

Parser edge cases live in these, so gather them on purpose:

- receipts from **≥3 different Belém supermarkets** (the M3 gate)
- one with a **weighed item** — bananas, meat: kg with 3 decimal places
- one with a **discount**, per-item and/or receipt-level
- one **large** receipt — does the item table paginate?
- one **small** receipt, 1–3 items
- if obtainable, one **contingency-emission** receipt (`tpEmis ≠ 1`)

### Deliverable

`docs/NFCE-PARA-FINDINGS.md` — answers to every question above, the chosen
path, and the raw evidence backing it.

---

## 6. Fixtures and privacy

Repository is **private**, which simplifies this. No sanitized/raw split, no
redaction tooling.

```
Fixtures/para/          committed, drives the tests
```

- **Consumer CPF** (`cDest` in the QR, or rendered on the page): **stripped at
  capture time**, always. It is personal data with no role in a parser test.
- **Store name / CNPJ:** kept. Public business registry data.
- **Access keys:** kept. Needed for tests, and they are the household's own
  receipts. Note each key remains a live public handle to that purchase — a
  reason to keep the repo private, not a reason to mangle the fixtures.

---

## 7. Initial data model

Deliberately close to the brief. Expect it to change once real NFC-e responses
are in hand — that is the point of doing M2 before M3.

```
Receipt              accessKey · issuerName · issuerCNPJ · purchasedAt
                     total · sourceURL · importedAt

ReceiptItem          receiptID · rawDescription · quantity · commercialUnit
                     unitPrice · totalPrice · gtin? · productCode?
                     canonicalProductID?

Product              normalizedName · category? · brand? · variant?
                     packageAmount? · packageUnit? · gtin?
```

**Deduplication** keys on the NFC-e access key. Re-scanning a receipt reports
*"This receipt has already been imported"* rather than creating duplicates.

**Normalization** stays a separate layer. Deterministic parsing and a
**persisted** raw-description → canonical-product mapping first; no LLM in the
loop to begin with. GTIN/EAN, where reliably present, is a strong identifier.

Canonical products should be shaped with the future shopping-list feature in
mind — but that feature is **not** built now and must not expand the MVP.

---

## 8. Milestones, and when the Mac is needed

| # | Milestone | Where | Exit gate |
|---|---|---|---|
| **M0** | Unblock: network allowlist, Swift toolchain, repo skeleton | Cloud | `swift test` runs |
| **M1** | QR payload + access-key decoder, offline, unit-tested | Cloud | tests green |
| **M2** | Live retrieval PoC; characterize transport A/B/C/D; capture fixtures | Cloud | `NFCE-PARA-FINDINGS.md` written |
| **M3** | HTML → `Receipt` + `[ReceiptItem]` parser against real fixtures | Cloud | **≥3 different supermarkets parse correctly** |
| **M4** | Xcode project, SwiftUI shell, camera scan, SwiftData, dedup | **Mac** | runs on physical iPhone |
| **M5** | Receipt review screen + monthly aggregation | Mac | |
| **M6** | Deterministic normalization + persisted mapping | mostly Cloud | |

### The Mac is not needed until M4

Everything through M3 — which is the project's actual success criterion — is
reachable from Windows/Cloud alone.

**Collecting test data needs no development at all.** The built-in iPhone
Camera app reads the NFC-e QR and displays the URL. Copy it, paste it into a
session. That is the entire data pipeline for M1–M3.

M3's exit gate is the gate to M4: do not start building UI until several real
receipts from different Belém supermarkets parse correctly.

---

## 9. Proposed repository structure

```
marketscan/
├── Packages/MarketScanCore/          # SwiftPM — Linux-testable, no Apple UI deps
│   ├── Sources/MarketScanCore/
│   │   ├── Fiscal/                   # AccessKey, QRPayload  (M1)
│   │   ├── Model/                    # Receipt, ReceiptItem, Product
│   │   ├── Provider/                 # NFCeProvider, ParaNFCeProvider
│   │   ├── Parsing/                  # HTML/XML → domain  (M3)
│   │   ├── Normalization/            # (M6)
│   │   ├── Aggregation/              # monthly totals  (M5)
│   │   └── Net/                      # HTTPClient protocol (D2)
│   └── Tests/MarketScanCoreTests/
├── Fixtures/para/                    # real captured receipts (§6)
├── Tools/                            # recon + capture scripts
├── App/                              # iOS app — created on the Mac at M4
│   ├── MarketScan.xcodeproj
│   └── MarketScan/                   # SwiftUI, SwiftData, camera
└── docs/
    ├── PLAN.md                       # this file
    └── NFCE-PARA-FINDINGS.md         # written during M2
```

Pipeline separation to preserve — no giant SwiftUI view:

```
QR acquisition → NFC-e URL interpretation → Pará retrieval → fiscal parsing
  → Receipt model → normalization → persistence → aggregation → SwiftUI
```

---

## 10. Out of scope

Not being built: Android, shopping lists, budgeting, nutrition tracking, price
comparison, supermarket recommendations, cloud sync, user accounts, family
sharing, receipt OCR, product barcode scanning, AI recommendations, App Store
infrastructure, support for other Brazilian states.

Also: no user account, no auth, no backend unless technically necessary, no
analytics, no subscriptions. Local-first. Test data must be easy to reset
during development.

---

## 11. Open questions

1. **Real QR host.** `appnfc.sefa.pa.gov.br` is unverified. Confirm from an
   actual receipt URL before finalizing the allowlist.
2. **QR `p=` layout** on current Pará receipts — normal vs. contingency.
3. **Transport path** A/B/C/D (§5).
4. **Item-table pagination** on large receipts.
5. **GTIN availability.** If the public consultation exposes EAN reliably,
   normalization gets much easier and §7's mapping layer gets much smaller.
6. **HTML parsing dependency.** Swift's built-in regex may suffice; a real HTML
   parser (e.g. SwiftSoup) would be the first dependency, justified only once
   M2 shows the markup is messy enough to need one.

---

## 12. Immediate next actions

- [ ] Add the three domains to the environment allowlist (§2), with the
      package-managers checkbox **checked**
- [ ] Start a fresh cloud session so the new policy applies
- [ ] Scan one receipt with the iPhone Camera app; paste the URL to confirm the
      real host before finalizing the allowlist
- [ ] Collect 5–10 real receipts per the diversity list in §5
- [ ] M0: install Swift, scaffold `MarketScanCore`, get `swift test` green
- [ ] M1: access-key + QR-payload decoder with tests
```
