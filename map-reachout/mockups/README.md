# Mockups

The field app is assembled from four fragments so the ~2,000-line script stays reviewable:

| part | contains |
|---|---|
| `parts/head.part` | HTML, CSS tokens (light/dark/system), phone frame, panels |
| `parts/script.part` | binary decoder → typed arrays; `/*__APP__*/` placeholder |
| `parts/app.part` | geometry, hulls, viewport culling, canvas rendering; `/*__UI__*/` |
| `parts/ui.part` | GPS, sheet, drawer, controls, boot |

`build_muni.py` concatenates them, substitutes the payload and municipality name, and
**fails the build** on duplicate DOM ids, missing `getElementById` targets, `getContext`
on a non-canvas, external URLs (blocked by CSP), or undefined CSS custom properties.

The admin panel is a single file, `parts/admin_shell.html`, with a `/*__DATA__*/` slot.

## Test before publishing

```bash
PAY=data/belem.bin.gz MAIN=muni_main.js node harness/ch.mjs   # field app
ADATA=data/vigia.admin.json          node harness/ah.mjs      # admin panel
```

Both run the **real** code against the **real** payload with a stubbed DOM and a real
`DecompressionStream`. They have caught a duplicate DOM id, a zero-size-canvas boot
failure, DPR-stale ghosting, and a crash on faces with no geometry — all of which passed
a casual eyeball.

Caveat: the stubs are approximations. When a harness result looks surprising, suspect the
harness first — several "bugs" during the session were stub limitations (non-recursive
child traversal, unmemoised `querySelectorAll`, a stubbed `setTimeout` that never fired).
