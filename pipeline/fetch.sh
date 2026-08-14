#!/usr/bin/env bash
# Download every source dataset. ~1.5 GB. Nothing here is committed.
# Usage:  bash pipeline/fetch.sh [MUNICIPIO_CODE ...]     (default: Belém + Vigia)
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p data && cd data

UF=PA
MUNS=("${@:-1501402 1508209}")

CNEFE=https://ftp.ibge.gov.br/Cadastro_Nacional_de_Enderecos_para_Fins_Estatisticos/Censo_Demografico_2022/Arquivos_CNEFE/GeoJSON/Municipio_20240910
GEO=https://geoftp.ibge.gov.br

echo "== CNEFE address points =="
for M in ${MUNS[@]}; do
  [ -f "cnefe_${M}.json.zip" ] || curl -# -o "cnefe_${M}.json.zip" \
    "$CNEFE/qg_810_endereco_Munic${M}.json.zip"
done

echo "== Base de Faces de Logradouros ($UF) =="
[ -f "${UF}_faces.zip" ] || curl -# -o "${UF}_faces.zip" \
  "$GEO/recortes_para_fins_estatisticos/malha_de_setores_censitarios/censo_2022/base_de_faces_de_logradouros_versao_2022_censo_demografico/json/${UF}_faces_de_logradouros_2022_json.zip"

echo "== Malha de bairros e distritos ($UF) =="
B=$GEO/organizacao_do_territorio/malhas_territoriais/malhas_de_setores_censitarios__divisoes_intramunicipais/censo_2022
[ -f "${UF}_bairros.gpkg" ]   || curl -# -o "${UF}_bairros.gpkg"   "$B/bairros/gpkg/UF/${UF}/${UF}_bairros_CD2022.gpkg"
[ -f "${UF}_distritos.gpkg" ] || curl -# -o "${UF}_distritos.gpkg" "$B/distritos/gpkg/UF/${UF}/${UF}_distritos_CD2022.gpkg"

echo
echo "== OpenStreetMap roads =="
echo "Not scripted: derive the bbox from the CNEFE points, then POST to Overpass."
echo "Overpass is frequently busy — retry, or use a mirror."
cat <<'EOF'
  python3 - <<'PY'
  import zipfile, json, sys
  z = zipfile.ZipFile(sys.argv[1] if len(sys.argv)>1 else 'cnefe_1501402.json.zip')
  pts = json.loads(z.open(z.namelist()[0]).read())['features']
  xs = [f['geometry']['coordinates'][0] for f in pts]
  ys = [f['geometry']['coordinates'][1] for f in pts]
  print('%.4f,%.4f,%.4f,%.4f' % (min(ys)-.01, min(xs)-.01, max(ys)+.01, max(xs)+.01))
  PY

  Q='[out:json][timeout:300][bbox:<BBOX>];(way["highway"];);out geom;'
  curl -s -X POST -d "data=$Q" https://overpass-api.de/api/interpreter -o roads_<MUN>.json
  # mirrors: overpass-api.kumi.systems, overpass.private.coffee
EOF

echo
echo "Optional, evaluated and not used in the build:"
echo "  Trajetos dos Recenseadores (GPS traces, too sparse to route from):"
echo "  $CNEFE/../../Trajetos_dos_Recenseadores/15_PARA.zip"
echo "  CODEM neighbourhood GeoPDFs (bairro outline only, no lotes):"
echo "  https://codem.belem.pa.gov.br/wp-content/uploads/2021/06/018_Guama.pdf"
