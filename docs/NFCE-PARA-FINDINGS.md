# Pará NFC-e — Findings

The M2 deliverable from PLAN.md §5. **In progress.** The QR payload is fully
characterized; the retrieval transport is not, because the host the QR points at
is currently unreachable.

| | |
|---|---|
| Status | QR layout resolved. Transport **unresolved** — `appnfc` host unreachable |
| Last updated | 2026-08-13 |
| Fixtures | 1 QR (`Fixtures/para/qr/receipt-01.txt`), 0 HTML |

---

## 1. Resolved: the QR code

### Host and path

```
https://appnfc.sefa.pa.gov.br/portal/view/consultas/nfce/nfceForm.seam?p=...
```

`appnfc.sefa.pa.gov.br` was a guess in the original plan. **Confirmed** from a
real receipt. The `.seam` extension confirms JBoss Seam/JSF, which is what
raised the odds of transport path B or C in §5; the portal identifies itself as
"Portal NFC 1.13.8".

### The `p=` payload

Five pipe-delimited fields — **QR code version 2, normal online emission**:

```
chNFe | nVersao | tpAmb | cIdToken | cHashQRCode
```

From `receipt-01`:

| Field | Value | Meaning |
|---|---|---|
| `chNFe` | `15260831671814000858651020005478671102541020` | 44-digit access key |
| `nVersao` | `2` | QR layout version |
| `tpAmb` | `1` | production |
| `cIdToken` | `1` | which CSC signed the QR |
| `cHashQRCode` | `44772474E995A5D08E243CFB0DC51279C5E6AE9D` | SHA-1, 40 hex chars |

Two consequences worth acting on:

- **No `cDest` field**, so this layout carries no consumer CPF. PLAN.md §6's
  stripping rule has nothing to strip *in this layout* — it still applies to the
  rendered page and to the contingency layout.
- **`cHashQRCode` cannot be verified locally.** It is computed with the issuer's
  secret contributor security code (CSC), which we do not hold. Preserve it and
  echo it back; do not attempt to validate it.

### The access key

Decoded offline, no network required. Both check-digit systems validate — the
key's own mod-11 digit and the issuer CNPJ's two digits.

| Field | Value |
|---|---|
| `cUF` | `15` — Pará |
| `AAMM` | `2608` — August 2026 |
| CNPJ | `31.671.814/0008-58` |
| `mod` | `65` — NFC-e |
| série | `102` |
| `nNF` | `547867` |
| `tpEmis` | `1` — normal online, not contingency |
| `cDV` | `0` — validates |

Implemented in `AccessKey` and `NFCeQRPayload`, 22 tests green.

### Still unresolved about the QR

The **contingency layout** (`tpEmis ≠ 1`) is unconfirmed and needs such a
receipt to settle. Until then `NFCeQRPayload` reports unrecognised field counts
as `.unverified(fieldCount:)` — raw fields preserved, no names invented.

---

## 2. Unresolved: the transport

### Reachability, measured 2026-08-13

Two independent vantage points, and they disagree in an informative way:

| Host | Claude Code cloud container | Belém desktop, Chrome |
|---|---|---|
| `www.sefa.pa.gov.br` | CONNECT 200, then **TCP reset** | ✅ **loads normally** |
| `appnfc.sefa.pa.gov.br` | CONNECT 200, then **TCP reset** | ❌ **ERR_CONNECTION_TIMED_OUT** |

This decomposes into **two separate problems**, which is easy to conflate:

**(a) The cloud container cannot reach SEFA at all.** Because `www` is confirmed
up from Brazil, the container's failure to reach it cannot be explained by the
server being down. Something on the path filters the container specifically —
most likely foreign or datacenter IP ranges, which is common for Brazilian state
fiscal portals. Supporting detail:

- DNS resolves correctly: `www` → `200.245.188.37`, `appnfc` → `.41`,
  `nfce` → `.47`, `app` → `.51`, all in SEFA-PA's range.
- The egress allowlist is confirmed correct: the proxy returns
  `200 Connection Established` for `*.sefa.pa.gov.br`, while
  `nfe.fazenda.gov.br` still cleanly `403`s.
- Fails in ~11s, on ports 80 and 443 alike, on all four subdomains.
- Forcing TLS 1.2, disabling ALPN, and lowering the cipher security level all
  fail identically — not a TLS mismatch with an old server.
- `WebFetch` fails the same way; it shares the same egress proxy.

**(b) `appnfc` is additionally unreachable from Brazil.** A Belém residential
connection that loads `www` fine times out on `appnfc`. Geography cannot explain
this one. Either the host is down, or it is reachable only from certain networks.
Since consumers must be able to scan these QR codes, an outage is the more likely
reading — in which case it should recover on its own.

### What this does *not* block

Decision D2 keeps networking out of Core and runs tests against committed
fixtures, so **M3 needs the saved HTML, not egress.** Once any vantage point
retrieves the page once, all parser work proceeds in the cloud.

### Candidate endpoints, untried

`www.sefa.pa.gov.br` is known to work from Brazil, so endpoints on that host are
the most promising. In rough priority order:

| # | URL | Why |
|---|---|---|
| 1 | `https://www.sefa.pa.gov.br/nfce/consulta` | On the host confirmed working |
| 2 | `http://nfce.sefa.pa.gov.br/` | Separate host, indexed as a live NFC-e entry point |
| 3 | `http://appnfc.sefa.pa.gov.br/...` (port 80) | Same host, in case only 443 is affected |
| 4 | `https://appnfc.sefa.pa.gov.br/portal/view/consultas/nfce/consultanfce.seam` | Manual key-entry form — note `consultanfce.seam`, **not** the QR's `nfceForm.seam` |
| 5 | Retry the original QR URL later | If (b) is an outage, it resolves itself |

Note that a CAPTCHA on the *manual key-entry* form would not imply one on the
*QR-URL* path: the QR's hash parameter typically authenticates that request.
PLAN.md §5 flags settling this distinction as an early job, and it remains open.

Third-party commercial APIs for SEFAZ-PA NFC-e consultation exist, which is
weak evidence that programmatic retrieval is feasible — path A or B rather than
D. Not evidence about *how*, and not a dependency we intend to take.

### Questions still open

Everything in PLAN.md §5's transport list, plus:

- Does the QR URL work from *any* network right now, or is `appnfc` simply down?
- Does `www.sefa.pa.gov.br/nfce/consulta` reach the same backend?
- Plain anonymous GET, or cookies / `ViewState` / redirects / JS / CAPTCHA?
- HTML, XML, or JSON?
- Item-table pagination on large receipts?
- Is GTIN/EAN exposed per item? This materially shrinks §7's mapping layer.

---

## 3. How to capture the HTML

From a machine that can reach the portal:

1. Open a URL from `Fixtures/para/qr/*.txt` (or a candidate above) in a browser.
2. Save the **complete** response — *Save page as → Webpage, HTML only* is
   enough; we want the server's markup, not a rendered snapshot.
3. Commit it to `Fixtures/para/html/` under the matching receipt name.
4. Record what it took to get there: redirects, cookies, `ViewState` tokens,
   whether JavaScript was required, whether a CAPTCHA appeared. **That
   narrative is the actual deliverable** — it decides path A/B/C/D — and the
   browser's Network tab is the place to read it off.

If the page renders only after JavaScript, note that explicitly: it forces path
C (`WKWebView` on-device) and shapes M4.
