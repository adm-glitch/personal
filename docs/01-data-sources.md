# Data sources

All free, all public, all verified by download during the design session (Aug 2026).
Nothing here requires a licence negotiation or a municipal contact.

## The spine

### 1. CNEFE 2022 — every address in Brazil, with coordinates
IBGE's Cadastro Nacional de Endereços para Fins Estatísticos, updated during the 2022 census.

```
https://ftp.ibge.gov.br/Cadastro_Nacional_de_Enderecos_para_Fins_Estatisticos/
  Censo_Demografico_2022/Arquivos_CNEFE/GeoJSON/Municipio_20240910/
  qg_810_endereco_Munic{CODIGO}.json.zip
```

**5,570 municipality files — every municipality in Brazil.** Also available per UF
(`UF_20240910/qg_810_endereco_UF{UF}.json.zip`; Pará entire = 133 MB) and as CSV.

Per address: `geometry` (lat/lon, EPSG:4674), `COD_UNICO_ENDERECO` (stable national id),
`LOGRAD_NUM` ("RUA X, 74"), `COMPLEMENTO`, `CEP`, `DSC_LOCALIDADE`, `COD_SETOR`,
`NUM_QUADRA`, `NUM_FACE`, `COD_ESPECIE`, `NV_GEO_COORD`.

`COD_ESPECIE`: 1 = private household (the one you want), 2 collective, 4 education,
5 health, 6 other establishment, 7 under construction, 8 religious.
`NV_GEO_COORD`: 1 = captured in the field by GPS.

### 2. Base de Faces de Logradouros 2022 — the kerbs, with a denominator
```
https://geoftp.ibge.gov.br/recortes_para_fins_estatisticos/malha_de_setores_censitarios/
  censo_2022/base_de_faces_de_logradouros_versao_2022_censo_demografico/json/
  {UF}_faces_de_logradouros_2022_json.zip
```
27 UF files. Per face: `CD_SETOR`, `CD_QUADRA`, `CD_FACE`, street name, and **`TOT_RES`**
— the census count of residences on that block-face. That is the coverage denominator.

Joins to CNEFE on `COD_SETOR`+`NUM_QUADRA`+`NUM_FACE`. **The join is not complete** —
see `02-findings.md`.

### 3. Malha de Bairros CD2022 — official neighbourhood polygons
```
https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/
  malhas_de_setores_censitarios__divisoes_intramunicipais/censo_2022/bairros/gpkg/UF/{UF}/
  {UF}_bairros_CD2022.gpkg
```
**25 UFs only** (DF and TO have none), and within those **only municipalities that
submitted a bairro division** — in Pará, 25 of 144. Belém has 72. Vigia has none.
When absent, fall back to `distritos/` (national coverage) plus CNEFE's
`DSC_LOCALIDADE`. This is the single biggest portability gotcha.

### 4. OpenStreetMap — the navigable street network
Overpass, per municipality bbox:
```
[out:json][timeout:300][bbox:{S},{W},{N},{E}];(way["highway"];);out geom;
```
Belém: 27,476 ways, 5,905 distinct names, **0.46 MB gzipped**. Road coverage is good
everywhere; **building** coverage is not — see findings.

## Secondary / evaluated and rejected

| source | verdict |
|---|---|
| **CODEM neighbourhood maps** (`codem.belem.pa.gov.br/mapas/`) | 71 real GeoPDFs (ArcMap 10, WGS84 UTM 22S, OGC `/Measure /GEO`). Layers are bairro boundary + labels only — **no lotes, no quadras**. Useful as a familiar overlay, useless as data. |
| **CODEM CTM** (lot-level cadastre) | ~360,000 properties, but DWG/DWF, **sold per sheet**, no open download. Not viable. |
| **SEFIN new cartographic base** | Being built from aerial imagery, unpublished. |
| **OSM buildings** | 148,026 in Belém but **27% coverage, inversely correlated with need** — 85% in Marco, **0% in Terra Firme**. Do not ship as a primary layer. |
| **IBGE Trajetos dos Recenseadores** | 2,555 GPS traces for Belém. Verified sparse and decimated in Belém, São Paulo *and* Belo Horizonte alike (73% of traces under 200 m in all three). **No route can be learned from it.** |
| **Satellite imagery** | Esri/Mapbox/Google all **prohibit offline caching** in third-party apps. Only legally cacheable option is **CBERS-4A WPM** (INPE, 2 m, orthorectified L4, Creative Commons, free registration) — usable as a backdrop, not for identifying doors. |

## Re-fetching

`pipeline/fetch.sh` pulls everything. Roughly 1.5 GB. None of it is committed;
`data/` holds only generated payloads.
