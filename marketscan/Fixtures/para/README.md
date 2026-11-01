# Pará NFC-e fixtures

Real captured receipts. These drive the tests — see docs/PLAN.md §6 for the
privacy rules and §5 for the diversity we are deliberately collecting.

```
qr/     scanned QR contents, one URL per file
html/   consultation responses saved from the portal  (M2, not yet captured)
```

## Privacy rules, restated

The repository is private, so there is no sanitized/raw split.

- **Consumer CPF is stripped at capture time, always.** It is personal data with
  no role in a parser test. Note that the QR version 2 *online* layout carries
  no `cDest` field at all, so receipts in that layout have no CPF to remove —
  but check the rendered page too, and check contingency payloads, which use a
  different field set.
- **Store name and CNPJ are kept.** Public business registry data.
- **Access keys are kept.** The tests need them, and these are the household's
  own receipts. Each key does remain a live public handle to that purchase,
  which is a reason to keep this repository private rather than a reason to
  mangle the fixtures.

## Inventory

| File | Issuer CNPJ | Série / nNF | Notable | Layout |
|---|---|---|---|---|
| `qr/receipt-01.txt` | `31.671.814/0008-58` | 102 / 547867 | uppercase hash | QR v2, online |
| `qr/receipt-02.txt` | `03.995.515/0225-60` | 21 / 132569 | **lowercase** hash; `cNF` has leading zeros | QR v2, online |

Both are Pará (`cUF=15`), August 2026, NFC-e (`mod=65`), normal online emission
(`tpEmis=1`), `tpAmb=1`, `cIdToken=1`. Every access key's mod-11 digit and every
issuer CNPJ's own check digits validate. Store names stay unknown until M2
retrieval — the QR carries only the CNPJ.

Two things these two receipts settled between them:

- The v2 online layout **holds across issuers and PDV vendors**, so it is not a
  one-store coincidence.
- The hash's hex **case varies by issuer** — uppercase in one, lowercase in the
  other. Stored verbatim, so compare case-insensitively.
- `cNF` can lead with zeros (`00191225`), which is why it is a `String` and not
  an `Int`.

## Still needed for the M3 gate

§5 calls for these on purpose, because the parser edge cases live in them:

- [ ] receipts from **≥3 different Belém supermarkets** — **2 of 3** so far
- [ ] one **weighed item** — kg to 3 decimal places
- [ ] one **discount**, per-item and/or receipt-level
- [ ] one **large** receipt, to see whether the item table paginates
- [ ] one **small** receipt, 1–3 items
- [ ] if obtainable, one **contingency emission** (`tpEmis ≠ 1`) — this is also
      the only way to confirm the second `p=` layout

## Capturing HTML (M2)

SEFA is unreachable from the Claude Code cloud container: the proxy permits the
connection but the upstream resets it, on every `*.sefa.pa.gov.br` host and on
port 80 and 443 alike. Verified 2026-08-13, including against the real
consultation endpoint.

So capture from a machine on a Brazilian connection: open the URL from
`qr/*.txt` in a browser, save the complete response into `html/`, and record
what it took to get there — redirects, cookies, `ViewState`, JavaScript,
CAPTCHA — in `docs/NFCE-PARA-FINDINGS.md`. That transport characterization is
M2's actual deliverable; the HTML is what unblocks M3 in the cloud.
