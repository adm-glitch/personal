#!/usr/bin/env python3
"""Fase 1: coleta completa do PNCP para os órgãos municipais de Belém (IBGE 1501402).

Uso:
  .venv/bin/python scripts/pncp_pull.py fetch [--run-date AAAA-MM-DD] [--phases search,contratacoes,orgaos,contratos,atas,termos,compras]
  .venv/bin/python scripts/pncp_pull.py load  [--run-date AAAA-MM-DD]

fetch: só rede. Cada resposta vai para raw/pncp/<run-date>/<fase>/<chave>.json (HTTP 204 = {"_status":204}).
       Se o arquivo já existe, a chamada é pulada: o script é retomável e idempotente. Log em requests.jsonl.
load:  só disco. Lê o bruto e (re)cria as tabelas orgaos, contratos, aditivos, contratacoes e atas em data/observatorio.duckdb.

Coleta educada: User-Agent identificado, >= 1,1 s entre requisições ao mesmo host, timeout de 150 s,
novas tentativas com espera crescente (o PNCP é lento e derruba conexões).

Escopo (pedido de 23/10/2026):
- órgãos: os 15 CNPJs municipais vistos na Fase 0 + qualquer órgão de esfera municipal (esferaId "M") com unidade
  em Belém que apareça na busca do PNCP ou nas contratações de 2026 por codigoMunicipioIbge=1501402;
- contratos: publicados no PNCP desde 2021 (início da Lei 14.133); a tabela marca os que tocam 2024-01-01..2026-12-31
  (publicação, assinatura ou vigência);
- termos (aditivos, apostilamentos, rescisões) de cada contrato no escopo;
- contratações (compras/editais) publicadas em 2026;
- atas de registro de preço dos órgãos (2024..hoje).
"""
import argparse, json, os, sys, time
from datetime import date, datetime, timedelta, timezone

import httpx

UA = "observatorio-belem/0.1 (pesquisa civica; contato via github adm-glitch)"
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DB = os.path.join(ROOT, "data", "observatorio.duckdb")
BASE = "https://pncp.gov.br"
IBGE = "1501402"
GAP = 1.1
BACKOFF = [5, 15, 45, 120]

SEED_CNPJS = {
    "05055033000152": "SEMEC", "49159407000155": "Guarda Municipal", "05055009000113": "Município de Belém",
    "05055009000628": "Município de Belém (filial)", "59815458000141": "SEGBEL", "04789822000154": "Saneamento",
    "07917818000112": "SESMA", "05065644000181": "Fundação Papa João XXIII", "05055025000106": "SEFIN",
    "59870569000150": "Secretaria da Mulher", "29331615000182": "Instituto de Previdência", "09551008000110": "SECONT",
    "59693965000150": "SECOM", "10245579000106": "Economia", "14700173000127": "Planejamento e Gestão",
}
MODALIDADES = range(1, 15)  # 1..14 (tabela de domínio do PNCP)
CONTRATOS_DESDE = 2021
ESCOPO_INI, ESCOPO_FIM = "2024-01-01", "2026-12-31"


class Fetcher:
    def __init__(self, run_dir: str):
        self.run_dir = run_dir
        self.client = httpx.Client(headers={"User-Agent": UA, "Accept": "application/json"},
                                   timeout=httpx.Timeout(150, connect=30), follow_redirects=True)
        self.last = 0.0
        self.log = open(os.path.join(run_dir, "requests.jsonl"), "a")

    def get(self, rel_path: str, url: str, params: dict | None = None, retries: int = len(BACKOFF)):
        """Devolve o JSON (dict/list) ou {"_status":204}; None se falhou de vez. Usa o cache em disco."""
        path = os.path.join(self.run_dir, rel_path)
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        for attempt in range(retries + 1):
            wait = GAP - (time.time() - self.last)
            if wait > 0:
                time.sleep(wait)
            self.last = time.time()
            t0 = time.time()
            entry = {"url": url, "params": params, "at": datetime.now(timezone.utc).isoformat(), "attempt": attempt}
            try:
                r = self.client.get(url, params=params)
                entry.update(status=r.status_code, elapsed_s=round(time.time() - t0, 2))
                if r.status_code == 204:
                    data = {"_status": 204}
                elif r.status_code == 200:
                    data = r.json()
                elif r.status_code == 404:
                    data = {"_status": 404}
                else:
                    raise httpx.HTTPStatusError(f"HTTP {r.status_code}", request=r.request, response=r)
                entry["file"] = rel_path
                self.log.write(json.dumps(entry, ensure_ascii=False) + "\n"); self.log.flush()
                with open(path + ".tmp", "w") as f:
                    json.dump(data, f, ensure_ascii=False)
                os.replace(path + ".tmp", path)
                return data
            except Exception as e:  # timeout, reset, 5xx, JSON inválido
                entry.update(error=f"{type(e).__name__}: {e}"[:300], elapsed_s=round(time.time() - t0, 2))
                self.log.write(json.dumps(entry, ensure_ascii=False) + "\n"); self.log.flush()
                if attempt < retries:
                    time.sleep(BACKOFF[min(attempt, len(BACKOFF) - 1)])
        print(f"  FALHOU: {url} {params}", file=sys.stderr)
        return None

    def paged(self, rel_prefix: str, url: str, params: dict, size: int = 50):
        """Itera as páginas de um endpoint de consulta (totalPaginas). Devolve (registros, ok)."""
        out, page, ok = [], 1, True
        while True:
            d = self.get(f"{rel_prefix}_p{page}.json", url, {**params, "pagina": page, "tamanhoPagina": size})
            if d is None:
                return out, False
            if d.get("_status") in (204, 404):
                break
            out.extend(d.get("data") or [])
            if page >= (d.get("totalPaginas") or 1):
                break
            page += 1
        return out, ok


def windows(y0: date, y1: date, months: int):
    cur = y0
    while cur <= y1:
        m = cur.month - 1 + months
        nxt = date(cur.year + m // 12, m % 12 + 1, 1)
        end = min(nxt - timedelta(days=1), y1)
        yield cur, end
        cur = nxt


def d8(d: date) -> str:
    return d.strftime("%Y%m%d")


def known_cnpjs(run_dir: str) -> dict:
    p = os.path.join(run_dir, "orgaos_descobertos.json")
    if os.path.exists(p):
        with open(p) as f:
            out = json.load(f)
    else:
        out = {c: {"nome": n, "fonte": "fase0"} for c, n in SEED_CNPJS.items()}
    p = os.path.join(run_dir, "orgaos_extra.json")  # escrito por completude.py (registro PNCP / Receita)
    if os.path.exists(p):
        with open(p) as f:
            for c, v in json.load(f).items():
                out.setdefault(c, v)
    return out


def save_cnpjs(run_dir: str, cnpjs: dict):
    with open(os.path.join(run_dir, "orgaos_descobertos.json"), "w") as f:
        json.dump(cnpjs, f, ensure_ascii=False, indent=1)


def fetch(run_date: str, phases: list[str]):
    run_dir = os.path.join(ROOT, "raw", "pncp", run_date)
    os.makedirs(run_dir, exist_ok=True)
    F = Fetcher(run_dir)
    cnpjs = known_cnpjs(run_dir)
    today = datetime.strptime(run_date, "%Y-%m-%d").date()

    if "search" in phases:
        print("[search] busca do site, contratos e atas municipais de Belém")
        for tipo in ("contrato", "ata"):
            for ordem in ("-data", "data"):
                page, fails = 1, 0
                while page <= 30 and fails < 2:
                    d = F.get(f"search/{tipo}_{'desc' if ordem.startswith('-') else 'asc'}_p{page}.json",
                              f"{BASE}/api/search/",
                              {"tipos_documento": tipo, "ordenacao": ordem, "pagina": page, "tam_pagina": 100,
                               "municipios": IBGE, "esferas": "M", "status": "todos"}, retries=1)
                    if d is None:
                        fails += 1
                        page += 1
                        continue
                    fails = 0
                    items = d.get("items") or []
                    for it in items:
                        c = it.get("orgao_cnpj")
                        if c and it.get("esfera_id") == "M" and it.get("codigo_ibge") == IBGE and c not in cnpjs:
                            cnpjs[c] = {"nome": it.get("orgao_nome"), "fonte": f"search:{tipo}"}
                            print(f"  novo órgão: {c} {it.get('orgao_nome')}")
                    if not items or page * 100 >= (d.get("total") or 0):
                        break
                    page += 1
        save_cnpjs(run_dir, cnpjs)

    if "contratacoes" in phases:
        print("[contratacoes] 2026 por município (todas as esferas; filtro M no load)")
        for mod in MODALIDADES:
            for a, b in windows(date(2026, 1, 1), today, 3):
                recs, ok = F.paged(f"contratacoes/ibge{IBGE}_mod{mod:02d}_{d8(a)}_{d8(b)}",
                                   f"{BASE}/api/consulta/v1/contratacoes/publicacao",
                                   {"dataInicial": d8(a), "dataFinal": d8(b), "codigoModalidadeContratacao": mod,
                                    "codigoMunicipioIbge": IBGE})
                n_m = 0
                for r in recs:
                    o = r.get("orgaoEntidade") or {}
                    if o.get("esferaId") == "M":
                        n_m += 1
                        if o.get("cnpj") not in cnpjs:
                            cnpjs[o["cnpj"]] = {"nome": o.get("razaoSocial"), "fonte": "contratacoes2026"}
                            print(f"  novo órgão: {o['cnpj']} {o.get('razaoSocial')}")
                print(f"  mod {mod:2d} {a}..{b}: {len(recs)} registros, {n_m} municipais{'' if ok else ' (INCOMPLETO)'}")
        save_cnpjs(run_dir, cnpjs)

    if "orgaos" in phases:
        print(f"[orgaos] cadastro de {len(cnpjs)} órgãos")
        for c in sorted(cnpjs):
            F.get(f"orgaos/{c}.json", f"{BASE}/api/pncp/v1/orgaos/{c}")
            F.get(f"orgaos/{c}_unidades.json", f"{BASE}/api/pncp/v1/orgaos/{c}/unidades")

    if "contratos" in phases:
        print(f"[contratos] {len(cnpjs)} órgãos, publicados {CONTRATOS_DESDE}..{today}")
        for c in sorted(cnpjs):
            tot = 0
            for y in range(CONTRATOS_DESDE, today.year + 1):
                a, b = date(y, 1, 1), min(date(y, 12, 31), today)
                recs, ok = F.paged(f"contratos/{c}_{y}", f"{BASE}/api/consulta/v1/contratos",
                                   {"dataInicial": d8(a), "dataFinal": d8(b), "cnpjOrgao": c})
                if not ok:  # janela anual falhou: tenta por trimestre
                    for qa, qb in windows(a, b, 3):
                        r2, _ = F.paged(f"contratos/{c}_{d8(qa)}_{d8(qb)}", f"{BASE}/api/consulta/v1/contratos",
                                        {"dataInicial": d8(qa), "dataFinal": d8(qb), "cnpjOrgao": c})
                        recs.extend(r2)
                tot += len(recs)
            print(f"  {c} {cnpjs[c]['nome']}: {tot}")

    if "atas" in phases:
        print(f"[atas] atas de registro de preço, {len(cnpjs)} órgãos, vigência/publicação 2024..{today}")
        for c in sorted(cnpjs):
            tot = 0
            for y in range(2024, today.year + 1):
                a, b = date(y, 1, 1), min(date(y, 12, 31), today)
                recs, ok = F.paged(f"atas/{c}_{y}", f"{BASE}/api/consulta/v1/atas",
                                   {"dataInicial": d8(a), "dataFinal": d8(b), "cnpj": c})
                tot += len(recs)
            print(f"  {c} {cnpjs[c]['nome']}: {tot}")

    contratos = None
    if "termos" in phases or "compras" in phases:
        contratos = list(iter_contratos(run_dir).values())

    if "termos" in phases:
        alvo = [k for k in contratos if in_scope(k)]
        print(f"[termos] {len(alvo)} contratos no escopo")
        for k in alvo:
            c, ano, seq = k["orgaoEntidade"]["cnpj"], k["anoContrato"], k["sequencialContrato"]
            F.get(f"termos/{c}_{ano}_{seq}.json", f"{BASE}/api/pncp/v1/orgaos/{c}/contratos/{ano}/{seq}/termos")

    if "compras" in phases:
        mods = modalidade_index(run_dir)
        falta = set()
        for k in contratos:
            if in_scope(k) and k.get("numeroControlePncpCompra") and k["numeroControlePncpCompra"] not in mods:
                falta.add(k["numeroControlePncpCompra"])
        print(f"[compras] {len(falta)} compras de origem sem modalidade conhecida")
        for ncp in sorted(falta):
            try:
                c, _, rest = ncp.split("-", 2)
                seq, ano = rest.split("/")
            except ValueError:
                continue
            F.get(f"compras/{c}_{ano}_{int(seq)}.json", f"{BASE}/api/consulta/v1/orgaos/{c}/compras/{ano}/{int(seq)}")
    print("fetch concluído")


# ---------- leitura do bruto ----------

def _json_files(d: str):
    if not os.path.isdir(d):
        return
    for fn in sorted(os.listdir(d)):
        if fn.endswith(".json"):
            with open(os.path.join(d, fn)) as f:
                yield fn, json.load(f)


def iter_contratos(run_dir: str) -> dict:
    """numeroControlePNCP -> registro mais recente (pela dataAtualizacao)."""
    out = {}
    for fn, d in _json_files(os.path.join(run_dir, "contratos")):
        for r in (d.get("data") or []) if isinstance(d, dict) else []:
            r["_file"] = f"contratos/{fn}"
            k = r["numeroControlePNCP"]
            if k not in out or (r.get("dataAtualizacao") or "") > (out[k].get("dataAtualizacao") or ""):
                out[k] = r
    return out


def in_scope(r: dict) -> bool:
    datas = [(r.get("dataPublicacaoPncp") or "")[:10], r.get("dataAssinatura") or ""]
    if any(ESCOPO_INI <= x <= ESCOPO_FIM for x in datas if x):
        return True
    ini, fim = r.get("dataVigenciaInicio") or r.get("dataAssinatura"), r.get("dataVigenciaFim")
    return bool(ini and fim and ini <= ESCOPO_FIM and fim >= ESCOPO_INI)


def modalidade_index(run_dir: str) -> dict:
    """numeroControlePNCP da compra -> (id, nome), a partir de contratações, busca e compras avulsas."""
    idx = {}
    for fn, d in _json_files(os.path.join(run_dir, "contratacoes")):
        for r in (d.get("data") or []) if isinstance(d, dict) else []:
            idx[r["numeroControlePNCP"]] = (r.get("modalidadeId"), r.get("modalidadeNome"))
    for fn, d in _json_files(os.path.join(run_dir, "compras")):
        if isinstance(d, dict) and d.get("numeroControlePNCP"):
            idx[d["numeroControlePNCP"]] = (d.get("modalidadeId"), d.get("modalidadeNome"))
    for fn, d in _json_files(os.path.join(run_dir, "search")):
        for it in (d.get("items") or []) if isinstance(d, dict) else []:
            k = it.get("numero_contratacao")
            if k and k not in idx and it.get("modalidade_licitacao_id"):
                idx[k] = (int(it["modalidade_licitacao_id"]), it.get("modalidade_licitacao_nome"))
    return idx


def classificar_registros(con):
    """O PNCP aceita, no tipo "Outros", atas, termos aditivos, rescisões e autorizações publicados como se fossem
    contratos (a SEMEC faz muito isso). Somar tudo infla o valor. Marca:
      tipo_registro: contrato | termo_aditivo | ata | rescisao | autorizacao | doacao
      conta_no_valor: entra nas somas de valor (contratos e termos aditivos, sem duplicata exata).
    Termo aditivo de prorrogação conta porque cobre um período novo de vigência; ata, rescisão e autorização repetem o
    valor de um contrato que já está na base. Duplicata: mesmo órgão, fornecedor, valor e número (sem zeros à esquerda)."""
    con.execute("ALTER TABLE contratos ADD COLUMN tipo_registro VARCHAR")
    con.execute("ALTER TABLE contratos ADD COLUMN conta_no_valor BOOLEAN")
    con.execute(r"""
        UPDATE contratos SET tipo_registro = CASE
          WHEN regexp_matches(upper(numero_contrato), 'RESCIS') OR regexp_matches(lower(objeto), 'rescis(ã|a)o (unilateral|consensual|amig)') THEN 'rescisao'
          WHEN regexp_matches(upper(numero_contrato), '\bATA\b') OR regexp_matches(lower(objeto), '^a presente ata de registro') THEN 'ata'
          WHEN regexp_matches(upper(numero_contrato), 'AUTORIZA') THEN 'autorizacao'
          WHEN regexp_matches(upper(numero_contrato), '\bTA\b|TA-|ADITIVO') OR regexp_matches(lower(objeto), 'termo aditivo') THEN 'termo_aditivo'
          WHEN regexp_matches(lower(objeto), 'doa(ç|c)(ã|a)o sem encargos') THEN 'doacao'
          ELSE 'contrato' END""")
    con.execute(r"""
        UPDATE contratos SET conta_no_valor = tipo_registro IN ('contrato', 'termo_aditivo') AND coalesce(valor_global, 0) > 0""")
    con.execute(r"""
        UPDATE contratos c SET conta_no_valor = false FROM (
          SELECT numero_controle_pncp, row_number() OVER (
                   PARTITION BY orgao_cnpj, fornecedor_ni, valor_global,
                                coalesce(nullif(ltrim(regexp_extract(numero_contrato, '\d+'), '0'), ''), numero_contrato)
                   ORDER BY data_publicacao, numero_controle_pncp) AS rn
            FROM contratos WHERE conta_no_valor) d
         WHERE c.numero_controle_pncp = d.numero_controle_pncp AND d.rn > 1""")


def load(run_date: str):
    import duckdb
    run_dir = os.path.join(ROOT, "raw", "pncp", run_date)
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    con = duckdb.connect(DB)
    extraido = run_date
    cnpjs = known_cnpjs(run_dir)
    contratos = iter_contratos(run_dir)
    mods = modalidade_index(run_dir)

    # search: modalidade direta por contrato (quando a compra não foi achada)
    mod_por_contrato = {}
    for fn, d in _json_files(os.path.join(run_dir, "search")):
        for it in (d.get("items") or []) if isinstance(d, dict) else []:
            if it.get("document_type") == "contrato" and it.get("modalidade_licitacao_id"):
                mod_por_contrato[it["numero_controle_pncp"]] = (int(it["modalidade_licitacao_id"]),
                                                                it.get("modalidade_licitacao_nome"))

    # órgãos
    rows = []
    for c, info in sorted(cnpjs.items()):
        p = os.path.join(run_dir, "orgaos", f"{c}.json")
        o = json.load(open(p)) if os.path.exists(p) else {}
        rows.append((c, o.get("razaoSocial") or info.get("nome"), info.get("nome"), o.get("poderId"), o.get("esferaId"),
                     info.get("fonte"), extraido))
    con.execute("CREATE OR REPLACE TABLE orgaos (cnpj VARCHAR PRIMARY KEY, razao_social VARCHAR, apelido VARCHAR, "
                "poder VARCHAR, esfera VARCHAR, fonte_descoberta VARCHAR, extraido_em DATE)")
    con.executemany("INSERT INTO orgaos VALUES (?,?,?,?,?,?,?)", rows)

    # contratos
    rows = []
    for k, r in contratos.items():
        o, u = r.get("orgaoEntidade") or {}, r.get("unidadeOrgao") or {}
        ncp = r.get("numeroControlePncpCompra")
        mid, mnome = mods.get(ncp) or mod_por_contrato.get(k) or (None, None)
        c, ano, seq = o.get("cnpj"), r.get("anoContrato"), r.get("sequencialContrato")
        rows.append((k, r.get("numeroContratoEmpenho"), ano, seq, c, o.get("razaoSocial"), o.get("esferaId"),
                     u.get("codigoUnidade"), u.get("nomeUnidade"), r.get("tipoPessoa"), r.get("niFornecedor"),
                     r.get("nomeRazaoSocialFornecedor"), r.get("objetoContrato"), r.get("valorInicial"),
                     r.get("valorGlobal"), r.get("valorAcumulado"), r.get("dataAssinatura"),
                     r.get("dataVigenciaInicio"), r.get("dataVigenciaFim"), (r.get("dataPublicacaoPncp") or "")[:10] or None,
                     (r.get("tipoContrato") or {}).get("nome"), (r.get("categoriaProcesso") or {}).get("nome"),
                     mid, mnome, ncp, r.get("processo"), r.get("numeroRetificacao"),
                     f"https://pncp.gov.br/app/contratos/{c}/{ano}/{seq}", in_scope(r), r["_file"], extraido))
    con.execute("""CREATE OR REPLACE TABLE contratos (
        numero_controle_pncp VARCHAR PRIMARY KEY, numero_contrato VARCHAR, ano INTEGER, sequencial INTEGER,
        orgao_cnpj VARCHAR, orgao_nome VARCHAR, orgao_esfera VARCHAR, unidade_codigo VARCHAR, unidade_nome VARCHAR,
        fornecedor_tipo VARCHAR, fornecedor_ni VARCHAR, fornecedor_nome VARCHAR, objeto VARCHAR,
        valor_inicial DOUBLE, valor_global DOUBLE, valor_acumulado DOUBLE, data_assinatura DATE,
        vigencia_inicio DATE, vigencia_fim DATE, data_publicacao DATE, tipo_contrato VARCHAR, categoria VARCHAR,
        modalidade_id INTEGER, modalidade_nome VARCHAR, numero_controle_compra VARCHAR, processo VARCHAR,
        numero_retificacao INTEGER, link_pncp VARCHAR, escopo_2024_2026 BOOLEAN, raw_file VARCHAR, extraido_em DATE)""")
    con.executemany("INSERT INTO contratos VALUES (" + ",".join("?" * 31) + ")", rows)
    classificar_registros(con)

    # aditivos / termos
    rows = []
    for fn, d in _json_files(os.path.join(run_dir, "termos")):
        if not isinstance(d, list):
            continue
        c, ano, seq = fn[:-5].split("_")
        for t in d:
            rows.append((f"{c}-2-{int(seq):06d}/{ano}", c, int(ano), int(seq), t.get("sequencialTermoContrato"),
                         t.get("numeroTermoContrato"), (t.get("tipoTermoContrato") or {}).get("nome") if isinstance(t.get("tipoTermoContrato"), dict) else t.get("tipoTermoContratoNome"),
                         t.get("objetoTermoContrato"), t.get("dataAssinatura"), t.get("dataVigenciaInicio"),
                         t.get("dataVigenciaFim"), t.get("valorAcrescido"), t.get("valorGlobal"),
                         t.get("prazoAditadoDias"), t.get("qualificacaoAcrescimoSupressao"),
                         t.get("qualificacaoVigencia"), t.get("qualificacaoReajuste"),
                         (t.get("dataPublicacaoPncp") or "")[:10] or None,
                         f"https://pncp.gov.br/app/contratos/{c}/{ano}/{seq}", json.dumps(t, ensure_ascii=False),
                         f"termos/{fn}", extraido))
    con.execute("""CREATE OR REPLACE TABLE aditivos (
        numero_controle_contrato VARCHAR, orgao_cnpj VARCHAR, ano_contrato INTEGER, sequencial_contrato INTEGER,
        sequencial_termo INTEGER, numero_termo VARCHAR, tipo_termo VARCHAR, objeto VARCHAR, data_assinatura DATE,
        vigencia_inicio DATE, vigencia_fim DATE, valor_acrescido DOUBLE, valor_global DOUBLE, prazo_aditado_dias INTEGER,
        qualif_acrescimo_supressao BOOLEAN, qualif_vigencia BOOLEAN, qualif_reajuste BOOLEAN, data_publicacao DATE,
        link_pncp VARCHAR, json VARCHAR, raw_file VARCHAR, extraido_em DATE)""")
    if rows:
        con.executemany("INSERT INTO aditivos VALUES (" + ",".join("?" * 22) + ")", rows)

    # contratações 2026 (só esfera municipal)
    seen = {}
    for fn, d in _json_files(os.path.join(run_dir, "contratacoes")):
        for r in (d.get("data") or []) if isinstance(d, dict) else []:
            o = r.get("orgaoEntidade") or {}
            if o.get("esferaId") != "M":
                continue
            k = r["numeroControlePNCP"]
            if k in seen and (seen[k][1].get("dataAtualizacao") or "") >= (r.get("dataAtualizacao") or ""):
                continue
            seen[k] = (fn, r)
    rows = []
    for k, (fn, r) in seen.items():
        o, u = r.get("orgaoEntidade") or {}, r.get("unidadeOrgao") or {}
        c, ano, seq = o.get("cnpj"), r.get("anoCompra"), r.get("sequencialCompra")
        rows.append((k, c, o.get("razaoSocial"), u.get("codigoUnidade"), u.get("nomeUnidade"), ano, seq,
                     r.get("numeroCompra"), r.get("processo"), r.get("modalidadeId"), r.get("modalidadeNome"),
                     (r.get("amparoLegal") or {}).get("nome"), r.get("srp"), r.get("objetoCompra"),
                     r.get("valorTotalEstimado"), r.get("valorTotalHomologado"), r.get("situacaoCompraNome"),
                     (r.get("dataPublicacaoPncp") or "")[:10] or None, (r.get("dataAberturaProposta") or "")[:10] or None,
                     f"https://pncp.gov.br/app/editais/{c}/{ano}/{seq}", f"contratacoes/{fn}", extraido))
    con.execute("""CREATE OR REPLACE TABLE contratacoes (
        numero_controle_pncp VARCHAR PRIMARY KEY, orgao_cnpj VARCHAR, orgao_nome VARCHAR, unidade_codigo VARCHAR,
        unidade_nome VARCHAR, ano INTEGER, sequencial INTEGER, numero_compra VARCHAR, processo VARCHAR,
        modalidade_id INTEGER, modalidade_nome VARCHAR, amparo_legal VARCHAR, srp BOOLEAN, objeto VARCHAR,
        valor_estimado DOUBLE, valor_homologado DOUBLE, situacao VARCHAR, data_publicacao DATE,
        data_abertura_proposta DATE, link_pncp VARCHAR, raw_file VARCHAR, extraido_em DATE)""")
    if rows:
        con.executemany("INSERT INTO contratacoes VALUES (" + ",".join("?" * 22) + ")", rows)

    # atas de registro de preço
    seen = {}
    for fn, d in _json_files(os.path.join(run_dir, "atas")):
        for r in (d.get("data") or []) if isinstance(d, dict) else []:
            k = r.get("numeroControlePNCPAta")
            if k:
                seen[k] = (fn, r)
    rows = [(k, r.get("cnpjOrgao"), r.get("nomeOrgao"), r.get("codigoUnidadeOrgao"), r.get("nomeUnidadeOrgao"),
             r.get("numeroAtaRegistroPreco"), r.get("anoAta"), r.get("numeroControlePNCPCompra"),
             r.get("objetoContratacao"), r.get("dataAssinatura"), r.get("vigenciaInicio"), r.get("vigenciaFim"),
             r.get("cancelado"), (r.get("dataPublicacaoPncp") or "")[:10] or None, f"atas/{fn}", extraido)
            for k, (fn, r) in seen.items()]
    con.execute("""CREATE OR REPLACE TABLE atas (
        numero_controle_pncp VARCHAR PRIMARY KEY, orgao_cnpj VARCHAR, orgao_nome VARCHAR, unidade_codigo VARCHAR,
        unidade_nome VARCHAR, numero_ata VARCHAR, ano INTEGER, numero_controle_compra VARCHAR, objeto VARCHAR,
        data_assinatura DATE, vigencia_inicio DATE, vigencia_fim DATE, cancelado BOOLEAN, data_publicacao DATE,
        raw_file VARCHAR, extraido_em DATE)""")
    if rows:
        con.executemany("INSERT INTO atas VALUES (" + ",".join("?" * 16) + ")", rows)

    for t in ("orgaos", "contratos", "aditivos", "contratacoes", "atas"):
        print(t, con.execute(f"SELECT count(*) FROM {t}").fetchone()[0])
    con.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["fetch", "load"])
    ap.add_argument("--run-date", default=datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    ap.add_argument("--phases", default="search,contratacoes,orgaos,contratos,atas,termos,compras")
    a = ap.parse_args()
    if a.cmd == "fetch":
        fetch(a.run_date, a.phases.split(","))
    else:
        load(a.run_date)


if __name__ == "__main__":
    main()
