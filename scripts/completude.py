#!/usr/bin/env python3
"""Fase 1: o PNCP está completo para Belém? Verificação de completude.

Uso:
  .venv/bin/python scripts/completude.py fetch  [--run-date AAAA-MM-DD]   # rede: SICONFI + unidades do registro PNCP
  .venv/bin/python scripts/completude.py report [--run-date AAAA-MM-DD]   # disco + DuckDB: imprime markdown

Três perguntas:
1. Órgãos: quais entidades municipais de Belém existem (Receita: natureza jurídica pública municipal com
   estabelecimento em Belém/PA; registro de órgãos do PNCP com unidade em 1501402) e quais têm contrato no PNCP.
   Também conta as unidades (secretarias que publicam sob o CNPJ do Município).
2. Valor: soma dos contratos PNCP vigentes em cada ano (pro rata pelos dias de vigência) contra a despesa do SICONFI
   (RREO Anexo 01) sem pessoal e sem dívida: outras despesas correntes + investimentos + inversões financeiras.
3. API x site: contratos por órgão na API de consulta (/v1/contratos) contra a busca do site (/api/search).

Escreve raw/pncp/<run-date>/orgaos_extra.json (CNPJs municipais de Belém achados aqui e ainda fora da coleta),
que o pncp_pull.py incorpora na fase de contratos.
"""
import argparse, json, os, sys, time, unicodedata
from datetime import date, datetime, timezone

import httpx

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pncp_pull import Fetcher, ROOT, DB, IBGE, known_cnpjs  # noqa: E402

SICONFI = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt"
# (ano, último bimestre disponível)
RREO = [(2024, 6), (2025, 6), (2026, 4)]
CONTAS_SEM_PESSOAL_DIVIDA = {"OutrasDespesasCorrentes": "Outras despesas correntes", "Investimentos": "Investimentos",
                             "InversoesFinanceiras": "Inversões financeiras"}
CONTAS_EXCLUIDAS = {"PessoalEEncargosSociais": "Pessoal e encargos", "JurosEEncargosDaDivida": "Juros da dívida",
                    "AmortizacaoDaDivida": "Amortização da dívida"}
NAT_MUN = {"1031": "Órgão do Executivo municipal", "1066": "Legislativo municipal", "1120": "Autarquia municipal",
           "1155": "Fundação pública municipal", "1180": "Órgão autônomo municipal", "1244": "Município",
           "1279": "Fundação pública de direito privado municipal", "1309": "Fundo da indireta municipal",
           "1333": "Fundo da direta municipal", "1210": "Consórcio público", "1228": "Consórcio público (privado)",
           "2011": "Empresa pública", "2038": "Sociedade de economia mista"}


FUNCOES = {"Legislativa", "Judiciária", "Essencial à Justiça", "Administração", "Segurança Pública", "Assistência Social",
           "Previdência Social", "Saúde", "Trabalho", "Educação", "Cultura", "Direitos da Cidadania", "Urbanismo",
           "Habitação", "Saneamento", "Gestão Ambiental", "Ciência e Tecnologia", "Agricultura", "Indústria",
           "Comércio e Serviços", "Comunicações", "Energia", "Transporte", "Desporto e Lazer", "Encargos Especiais"}
ORGAO_FUNCAO = {"07917818000112": "Saúde", "05055033000152": "Educação", "04789822000154": "Saneamento",
                "49159407000155": "Segurança Pública", "59815458000141": "Segurança Pública",
                "05065644000181": "Assistência Social", "29331615000182": "Previdência Social"}


def n(s):
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().upper()


def fetch(run_date):
    pncp_dir = os.path.join(ROOT, "raw", "pncp", run_date)
    sic_dir = os.path.join(ROOT, "raw", "siconfi", run_date)
    os.makedirs(sic_dir, exist_ok=True)
    S = Fetcher(sic_dir)
    for ano, per in RREO:
        for anexo in ("RREO-Anexo 01", "RREO-Anexo 02"):
            S.get(f"rreo_{ano}_p{per}_{anexo[-2:]}.json", f"{SICONFI}/rreo",
                  {"an_exercicio": ano, "nr_periodo": per, "co_tipo_demonstrativo": "RREO", "no_anexo": anexo,
                   "co_esfera": "M", "id_ente": IBGE})
    # registro completo de órgãos do PNCP (o filtro razaoSocial é ignorado pela API: vem tudo, ~98 mil)
    P = Fetcher(pncp_dir)
    reg = P.get("orgaos_todos_registro.json", "https://pncp.gov.br/api/pncp/v1/orgaos", {"razaoSocial": "BELEM", "pagina": 1})
    cand = [o for o in reg if o.get("esferaId") == "M" and "BELEM" in n(o.get("razaoSocial"))]
    extra = {}
    have = known_cnpjs(pncp_dir)
    rec = receita_municipais()
    alvo = {o["cnpj"] for o in cand} | {c for c in rec if c in {o["cnpj"] for o in reg}}
    print(f"{len(alvo)} órgãos do registro PNCP a checar (nome com BELEM ou entidade municipal de Belém na Receita)")
    for c in sorted(alvo):
        u = P.get(f"orgaos/{c}_unidades.json", f"https://pncp.gov.br/api/pncp/v1/orgaos/{c}/unidades")
        em_belem = isinstance(u, list) and any(str(x.get("municipio", {}).get("codigoIbge")) == IBGE for x in u)
        if (em_belem or c in rec) and c not in have:
            nome = next((o["razaoSocial"] for o in reg if o["cnpj"] == c), "")
            extra[c] = {"nome": nome, "fonte": "registro-pncp" + ("+receita" if c in rec else "")}
    with open(os.path.join(pncp_dir, "orgaos_extra.json"), "w") as f:
        json.dump(extra, f, ensure_ascii=False, indent=1)
    print(f"{len(extra)} órgãos municipais de Belém no registro PNCP ainda fora da coleta -> orgaos_extra.json")


def receita_municipais() -> dict:
    """CNPJ (14) -> info, das entidades de natureza pública municipal com estabelecimento em Belém/PA."""
    try:
        import duckdb
        con = duckdb.connect(DB, read_only=True)
        tabs = {r[0] for r in con.execute("SELECT table_name FROM information_schema.tables").fetchall()}
        if not {"empresas", "estabelecimentos", "municipios"} <= tabs:
            con.close()
            return {}
        nats = ",".join(f"'{k}'" for k in NAT_MUN)
        rows = con.execute(f"""
            SELECT s.cnpj, e.razao_social, e.natureza_juridica, s.identificador_matriz_filial, s.situacao_cadastral,
                   s.nome_fantasia, e.ente_federativo_responsavel
              FROM estabelecimentos s JOIN empresas e USING (cnpj_basico)
              JOIN municipios m ON m.codigo = s.municipio
             WHERE e.natureza_juridica IN ({nats}) AND s.uf = 'PA' AND m.descricao = 'BELEM'
               AND (e.natureza_juridica NOT IN ('2011','2038','1210','1228')
                    OR upper(e.razao_social) LIKE '%BELEM%')""").fetchall()
        con.close()
        return {r[0]: {"razao_social": r[1], "natureza": r[2], "matriz": r[3] == "1", "situacao": r[4],
                       "fantasia": r[5], "ente": r[6]} for r in rows}
    except Exception as e:
        print(f"(Receita indisponível: {e})", file=sys.stderr)
        return {}


def brl(v):
    return "R$ " + f"{v:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")


def report(run_date):
    import duckdb
    pncp_dir = os.path.join(ROOT, "raw", "pncp", run_date)
    sic_dir = os.path.join(ROOT, "raw", "siconfi", run_date)
    con = duckdb.connect(DB, read_only=True)
    out = []
    p = out.append

    # ---- 1. órgãos
    reg = json.load(open(os.path.join(pncp_dir, "orgaos_todos_registro.json")))
    reg_idx = {o["cnpj"]: o for o in reg}
    rec = receita_municipais()
    cont = {r[0]: r[1:] for r in con.execute("""
        SELECT orgao_cnpj, count(*), count(*) FILTER (escopo_2024_2026), count(DISTINCT unidade_codigo),
               max(orgao_nome) FROM contratos GROUP BY 1""").fetchall()}
    coleta = known_cnpjs(pncp_dir)
    todos = set(rec) | set(cont) | set(coleta)
    rows = []
    for c in todos:
        r = rec.get(c, {})
        nome = r.get("razao_social") or (reg_idx.get(c) or {}).get("razaoSocial") or (cont.get(c) or [None] * 4)[3] or coleta.get(c, {}).get("nome")
        k = cont.get(c, (0, 0, 0, None))
        rows.append((c, nome, NAT_MUN.get(r.get("natureza") or (reg_idx.get(c) or {}).get("codigoNaturezaJuridica"), ""),
                     r.get("situacao", ""), "sim" if c in reg_idx else "não", k[0], k[1], k[2]))
    rows.sort(key=lambda x: (-x[5], x[1] or ""))
    sit = {"01": "nula", "02": "ativa", "03": "suspensa", "04": "inapta", "08": "baixada"}
    p(f"Universo: {len(rec)} estabelecimentos de natureza pública municipal com endereço em Belém/PA na base CNPJ "
      f"(Receita, 2026-10), {sum(1 for c in rec if c in reg_idx)} deles no registro de órgãos do PNCP; "
      f"{sum(1 for r in rows if r[5] > 0)} CNPJs com ao menos um contrato no PNCP.\n")
    ativos = [r for r in rows if r[3] in ("", "02")]
    p("| CNPJ | Entidade | Natureza | Situação Receita | No registro PNCP | Contratos PNCP (total) | No escopo 2024–26 | Unidades com contrato |")
    p("|---|---|---|---|---|---:|---:|---:|")
    for r in ativos:
        p(f"| `{r[0]}` | {r[1]} | {r[2]} | {sit.get(r[3], r[3]) or '—'} | {r[4]} | {r[5]} | {r[6]} | {r[7]} |")
    p(f"\n{len(rows) - len(ativos)} estabelecimentos baixados/inaptos/nulos omitidos da tabela.\n")
    p("Unidades (códigos de unidade gestora) com contrato no PNCP:\n")
    p("| Órgão (CNPJ) | Unidade | Contratos | No escopo |")
    p("|---|---|---:|---:|")
    for r in con.execute("""SELECT orgao_cnpj, unidade_codigo || ' ' || max(unidade_nome), count(*),
                                   count(*) FILTER (escopo_2024_2026) FROM contratos GROUP BY 1, unidade_codigo
                             ORDER BY 1, 3 DESC""").fetchall():
        p(f"| `{r[0]}` | {r[1]} | {r[2]} | {r[3]} |")

    # ---- 2. valor
    p("\n### Valor\n")
    p("| Ano | Despesa SICONFI sem pessoal e dívida, empenhada | idem, liquidada | Período | Contratos PNCP vigentes (pro rata no período) | Cobertura (pro rata ÷ empenhado) | Soma bruta do valor global dos vigentes |")
    p("|---|---:|---:|---|---:|---:|---:|")
    for ano, per in RREO:
        f = os.path.join(sic_dir, f"rreo_{ano}_p{per}_01.json")
        if not os.path.exists(f):
            continue
        items = json.load(open(f)).get("items", [])
        def val(contas, col):
            return sum(i["valor"] or 0 for i in items if i["cod_conta"] in contas and i["coluna"].startswith(col))
        emp = val(CONTAS_SEM_PESSOAL_DIVIDA, "DESPESAS EMPENHADAS ATÉ")
        liq = val(CONTAS_SEM_PESSOAL_DIVIDA, "DESPESAS LIQUIDADAS ATÉ")
        ini, fim = date(ano, 1, 1), date(ano, per * 2, 28 if per * 2 == 2 else 30 if per * 2 in (4, 6, 9, 11) else 31)
        pro, bruto = con.execute("""
            SELECT sum(valor_global * (least(vigencia_fim, ?::DATE) - greatest(vigencia_inicio, ?::DATE) + 1)
                       / greatest(vigencia_fim - vigencia_inicio + 1, 1)),
                   sum(valor_global)
              FROM contratos WHERE vigencia_inicio <= ? AND vigencia_fim >= ? AND conta_no_valor""",
                                 [fim, ini, fim, ini]).fetchone()
        pro, bruto = pro or 0, bruto or 0
        p(f"| {ano} | {brl(emp)} | {brl(liq)} | jan–{['', 'fev', 'abr', 'jun', 'ago', 'out', 'dez'][per]} | {brl(pro)} | "
          f"{100 * pro / emp:.1f}% | {brl(bruto)} |")
        excl = {v: val({k: v}, "DESPESAS EMPENHADAS ATÉ") for k, v in CONTAS_EXCLUIDAS.items()}
        p(f"|  | excluído: " + "; ".join(f"{k} {brl(v)}" for k, v in excl.items()) + " |  |  |  |  |  |")

    # por função (2026), com o PNCP agrupado por órgão -> função (aproximação: o órgão da secretaria finalística)
    f = os.path.join(sic_dir, "rreo_2026_p4_02.json")
    if os.path.exists(f):
        items = json.load(open(f)).get("items", [])
        emp_f = {}
        for i in items:
            if i["coluna"].startswith("DESPESAS EMPENHADAS ATÉ") and i["conta"] in FUNCOES and i["conta"] not in emp_f:
                emp_f[i["conta"]] = i["valor"] or 0
        pro_f = {}
        for c, v in con.execute("""
            SELECT orgao_cnpj, sum(valor_global * (least(vigencia_fim, DATE '2026-08-31') - greatest(vigencia_inicio, DATE '2026-01-01') + 1)
                       / greatest(vigencia_fim - vigencia_inicio + 1, 1))
              FROM contratos WHERE vigencia_inicio <= DATE '2026-08-31' AND vigencia_fim >= DATE '2026-01-01'
               AND conta_no_valor GROUP BY 1""").fetchall():
            fn = ORGAO_FUNCAO.get(c, "outros órgãos (Administração e demais)")
            pro_f[fn] = pro_f.get(fn, 0) + (v or 0)
        p("\nPor função, jan–ago/2026. Atenção: o RREO Anexo 02 **inclui pessoal**, então a razão é um piso, não uma cobertura; "
          "o PNCP foi agrupado pelo órgão contratante (SESMA→Saúde, SEMEC→Educação, Saneamento→Saneamento, "
          "Guarda/SEGBEL→Segurança Pública), o que é aproximado.\n")
        p("| Função | Empenhado SICONFI jan–ago/2026 (com pessoal) | Contratos PNCP pro rata jan–ago/2026 | Razão |")
        p("|---|---:|---:|---:|")
        for fn, v in sorted(emp_f.items(), key=lambda x: -x[1]):
            if v < 20e6:
                continue
            pv = pro_f.get(fn, 0)
            p(f"| {fn} | {brl(v)} | {brl(pv)} | {100 * pv / v:.1f}% |")
        if "outros órgãos (Administração e demais)" in pro_f:
            p(f"| (contratos de outros órgãos) | — | {brl(pro_f['outros órgãos (Administração e demais)'])} | — |")

    # ---- 3. API x site
    p("\n### API de consulta × busca do site\n")
    s_cnt = {}
    for fn in sorted(os.listdir(os.path.join(pncp_dir, "search"))):
        d = json.load(open(os.path.join(pncp_dir, "search", fn)))
        for it in d.get("items") or []:
            if it.get("document_type") == "contrato":
                s_cnt.setdefault(it["orgao_cnpj"], set()).add(it["numero_controle_pncp"])
    api = {r[0]: set(r[1]) for r in con.execute(
        "SELECT orgao_cnpj, list(numero_controle_pncp) FROM contratos GROUP BY 1").fetchall()}
    total_site = None
    for fn in sorted(os.listdir(os.path.join(pncp_dir, "search"))):
        if fn.startswith("contrato_"):
            total_site = json.load(open(os.path.join(pncp_dir, "search", fn))).get("total")
            break
    p(f"Busca do site (`/api/search`, municípios=1501402, esfera M, todos os status): total declarado {total_site}, "
      f"{sum(len(v) for v in s_cnt.values())} contratos distintos baixados.\n")
    p("| Órgão | API consulta | Busca do site | Só na API | Só no site |")
    p("|---|---:|---:|---:|---:|")
    for c in sorted(set(api) | set(s_cnt), key=lambda c: -len(api.get(c, ()))):
        a, s = api.get(c, set()), s_cnt.get(c, set())
        p(f"| `{c}` {coleta.get(c, {}).get('nome', '')} | {len(a)} | {len(s)} | {len(a - s)} | {len(s - a)} |")
    so_site = set().union(*s_cnt.values()) - set().union(*api.values()) if api and s_cnt else set()
    if so_site:
        p(f"\nContratos que aparecem na busca e não na API: {', '.join(sorted(so_site)[:20])}")
    con.close()
    txt = "\n".join(out)
    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    with open(os.path.join(ROOT, "data", "completude.md"), "w") as f:
        f.write(txt)
    print(txt)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["fetch", "report"])
    ap.add_argument("--run-date", default=datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    a = ap.parse_args()
    fetch(a.run_date) if a.cmd == "fetch" else report(a.run_date)


if __name__ == "__main__":
    main()
