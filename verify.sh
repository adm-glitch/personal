#!/usr/bin/env bash
# Smoke test: regenerate payloads from source, rebuild all four artifacts, run both
# harnesses. If this passes, the pipeline is intact.
#   bash verify.sh            # Vigia only (fast, ~5 s)
#   bash verify.sh --full     # Vigia + Belém (~40 s)
set -euo pipefail
cd "$(dirname "$0")"
FULL=${1:-}

need() { [ -f "data/$1" ] || { echo "MISSING data/$1 — run: bash pipeline/fetch.sh"; exit 1; }; }
need PA_faces.zip; need PA_bairros.gpkg; need PA_distritos.gpkg; need PA_setores.gpkg
need cnefe_1508209.json.zip; need roads_1508209.json

run() {  # code name cnefe roads prefix nblab
  echo "── $2 ─────────────────────────────"
  python3 pipeline/gen_muni.py "$1" "$2" "$3" "$4" "$5"
  python3 mockups/build_muni.py "data/$5" "$2" "$6" "$5_app.html" "lede" "eyebrow"
  python3 mockups/build_admin.py "data/$5.admin.json" "$5_admin.html"
  PAY="data/$5.bin.gz" MAIN=muni_main.js node mockups/harness/ch.mjs | tail -1
  ADATA="data/$5.admin.json"          node mockups/harness/ah.mjs  | tail -1
  echo
}

run 1508209 "Vigia" cnefe_1508209.json.zip roads_1508209.json vigia "55 localidades"

if [ "$FULL" = "--full" ]; then
  need cnefe_1501402.json.zip; need roads_1501402.json
  run 1501402 "Belém" cnefe_1501402.json.zip roads_1501402.json belem "71 bairros"
  echo "── Belém, hand-tuned published payload ─────────────"
  python3 pipeline/gen_admin.py
  ADATA=data/belem-published.admin.json node mockups/harness/ah.mjs | tail -1
  echo
fi

echo "OK — payloads regenerated, artifacts rebuilt, harnesses green."
