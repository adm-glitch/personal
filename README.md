# marketscan

Brazilian grocery receipt scanner (NFC-e), iOS. Scans the QR code on a
supermarket receipt and turns the purchased items into structured data.

**Scope: Pará only** (UF code 15). Other states are explicitly out of scope.

See [`docs/PLAN.md`](docs/PLAN.md) for the full implementation plan — the
architecture decisions, milestones, and open questions all live there, and it is
the shared reference across the Windows/Cloud and Mac/Xcode checkouts.

## Status

| Milestone | State |
|---|---|
| **M0** — toolchain, repo skeleton | ✅ done |
| **M1** — access-key + QR payload decoder | ✅ done, 22 tests green |
| **M2** — live retrieval PoC | ⛔ blocked: needs receipt HTML captured on a Brazilian connection |
| **M3** — HTML → receipt parser | blocked on M2 fixtures |
| M4–M6 — iOS app, aggregation, normalization | not started |

The success criterion is M3, not the UI: *given a real NFC-e QR code from a
Belém supermarket, reliably retrieve and parse the purchased items.*

## Layout

```
Packages/MarketScanCore/   core logic — no Apple-UI deps, tests on Linux
Fixtures/para/             real captured receipts (see its README for privacy rules)
Tools/                     setup and recon scripts
docs/PLAN.md               the plan
App/                       iOS app — created on the Mac at M4
```

Core deliberately performs no networking and holds no Apple-only types, so the
bulk of the project builds and tests on Linux. See decisions D1–D3 in the plan
for why.

## Building

Needs a Swift 6 toolchain. On Linux:

```bash
Tools/setup-swift.sh                        # installs to /opt/swift
export PATH="/opt/swift/usr/bin:$PATH"

cd Packages/MarketScanCore
swift build
swift test
```

On macOS, open `Packages/MarketScanCore/Package.swift` in Xcode, or run the same
`swift build` / `swift test` commands.

## What's needed next

Open the URL in `Fixtures/para/qr/receipt-01.txt` in a browser **on a Brazilian
connection**, save the complete HTML response into `Fixtures/para/html/`, and
note what it took to load — redirects, cookies, `ViewState`, JavaScript,
CAPTCHA. SEFA is unreachable from the cloud container (plan §2), so this one
step has to happen locally. It unblocks both M2 and M3.

Beyond that, more receipts: the M3 gate needs **≥3 different Belém
supermarkets** and there is currently 1.
