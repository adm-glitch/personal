#!/usr/bin/env python3
"""Fase 1: tabelas da primeira amostra (PNCP x CNPJ x CEIS/CNEP), em markdown, a partir do DuckDB.

Uso: .venv/bin/python scripts/fase1_amostra.py > data/fase1_tabelas.md

Regras: só pessoa jurídica no ranking; sócios com nome e qualificação do QSA, NUNCA o CPF (nem mascarado);
valores somam só os registros com conta_no_valor (contratos e termos aditivos, sem atas, rescisões, autorizações
nem duplicatas; ver pncp_pull.classificar_registros).
"""
import os, sys

import duckdb

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
con = duckdb.connect(os.path.join(ROOT, "data", "observatorio.duckdb"), read_only=True)
P = print
PORTE = {"00": "não informado", "01": "ME", "03": "EPP", "05": "demais"}


def brl(v):
    return "R$ " + f"{(v or 0):,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")


def q(sql, *a):
    return con.execute(sql, list(a)).fetchall()


# ---------- contagens
P("## Contagens\n")
P(f"- Órgãos verificados no PNCP: {q('SELECT count(*) FROM orgaos')[0][0]}; com contrato: "
  f"{q('SELECT count(DISTINCT orgao_cnpj) FROM contratos')[0][0]}")
P(f"- Registros de contrato: {q('SELECT count(*) FROM contratos')[0][0]} "
  f"(no escopo 2024–2026: {q('SELECT count(*) FROM contratos WHERE escopo_2024_2026')[0][0]})")
P(f"- Termos (endpoint /termos): {q('SELECT count(*) FROM aditivos')[0][0]}; contratações municipais publicadas em 2026: "
  f"{q('SELECT count(*) FROM contratacoes')[0][0]}\n")
P("| Tipo de registro | Registros | Soma do valor global | Entra nas somas |")
P("|---|---:|---:|---|")
for t, n, v, c in q("""SELECT tipo_registro, count(*), sum(valor_global), bool_or(conta_no_valor) FROM contratos
                      GROUP BY 1 ORDER BY 2 DESC"""):
    P(f"| {t} | {n} | {brl(v)} | {'sim' if c else 'não'} |")
P("\nPor ano de assinatura (só registros que entram nas somas):\n")
P("| Ano | Registros | Valor global |")
P("|---|---:|---:|")
for y, n, v in q("""SELECT year(data_assinatura), count(*), sum(valor_global) FROM contratos WHERE conta_no_valor
                      GROUP BY 1 ORDER BY 1"""):
    P(f"| {y} | {n} | {brl(v)} |")
P("\nVigentes em 2026 (vigência toca 2026), por órgão:\n")
P("| Órgão | CNPJ | Registros | Valor global | Pro rata 2026 |")
P("|---|---|---:|---:|---:|")
tot = [0, 0, 0]
for o, c, n, v, pr in q("""
    SELECT max(orgao_nome), orgao_cnpj, count(*), sum(valor_global),
           sum(valor_global * (least(vigencia_fim, DATE '2026-12-31') - greatest(vigencia_inicio, DATE '2026-01-01') + 1)
               / greatest(vigencia_fim - vigencia_inicio + 1, 1))
      FROM contratos WHERE conta_no_valor AND vigencia_inicio <= DATE '2026-12-31' AND vigencia_fim >= DATE '2026-01-01'
     GROUP BY 2 ORDER BY 4 DESC"""):
    P(f"| {o} | `{c}` | {n} | {brl(v)} | {brl(pr)} |")
    tot = [tot[0] + n, tot[1] + v, tot[2] + pr]
P(f"| **Total** | | **{tot[0]}** | **{brl(tot[1])}** | **{brl(tot[2])}** |")

# ---------- top 20
tabs = {r[0] for r in q("SELECT table_name FROM information_schema.tables")}
has_cnpj = {"empresas", "estabelecimentos", "socios"} <= tabs
top = q("""
    SELECT fornecedor_ni, max(fornecedor_nome), sum(valor_global), count(*), list(DISTINCT orgao_nome),
           list(objeto ORDER BY valor_global DESC), list(link_pncp ORDER BY valor_global DESC)
      FROM contratos
     WHERE conta_no_valor AND fornecedor_tipo = 'PJ'
       AND vigencia_inicio <= DATE '2026-12-31' AND vigencia_fim >= DATE '2026-01-01'
     GROUP BY 1 ORDER BY 3 DESC LIMIT 20""")
P("\n## 20 maiores fornecedores (PJ), contratos vigentes em 2026\n")
for i, (ni, nome, v, n, orgs, objs, links) in enumerate(top, 1):
    P(f"### {i}. {nome} — `{ni[:2]}.{ni[2:5]}.{ni[5:8]}/{ni[8:12]}-{ni[12:]}`\n")
    P(f"- **Contratado (valor global, vigentes em 2026):** {brl(v)} em {n} registro(s) · órgãos: {'; '.join(orgs)}")
    obj = " | ".join(" ".join((o or "").split())[:140] for o in objs[:3])
    P(f"- **Objetos (resumo, maiores primeiro):** {obj}")
    P(f"- **PNCP:** {' · '.join(links[:3])}")
    if has_cnpj:
        b = ni[:8]
        e = q("""SELECT e.razao_social, e.capital_social, e.porte_empresa, n.descricao FROM empresas e
                   LEFT JOIN naturezas n ON n.codigo = e.natureza_juridica WHERE cnpj_basico = ?""", b)
        s = q("""SELECT s.data_abertura, s.cnae_fiscal_principal, c.descricao, s.situacao_cadastral, m.descricao, s.uf
                   FROM estabelecimentos s LEFT JOIN cnaes c ON c.codigo = s.cnae_fiscal_principal
                   LEFT JOIN municipios m ON m.codigo = s.municipio WHERE s.cnpj = ?""", ni)
        mei = q("SELECT opcao_mei, opcao_pelo_simples FROM simples WHERE cnpj_basico = ?", b) if "simples" in tabs else []
        if e:
            rs, cap, porte, nat = e[0]
            P(f"- **Receita:** {nat}; porte {PORTE.get(porte, porte)}"
              f"{'; MEI' if mei and mei[0][0] == 'S' else ''}{'; Simples' if mei and mei[0][1] == 'S' else ''}; "
              f"capital social {brl(cap)}")
        if s:
            ab, cnae, cdesc, sit, mun, uf = s[0]
            sitd = {"02": "ativa", "03": "suspensa", "04": "inapta", "08": "baixada", "01": "nula"}.get(sit, sit)
            P(f"- **Abertura:** {ab:%d/%m/%Y} · **CNAE principal:** {cnae} {cdesc} · situação {sitd} · sede {mun}/{uf}"
              if ab else f"- **CNAE principal:** {cnae} {cdesc} · situação {sitd} · sede {mun}/{uf}")
        soc = q("""SELECT s.nome_socio_razao_social, q.descricao, s.data_entrada_sociedade, s.identificador_socio
                     FROM socios s LEFT JOIN qualificacoes q ON q.codigo = s.qualificacao_socio
                    WHERE s.cnpj_basico = ? ORDER BY s.data_entrada_sociedade""", b)
        if soc:
            P("- **Sócios (QSA):** " + "; ".join(
                f"{nm} ({qd}, desde {d[6:]}/{d[4:6]}/{d[:4]})" if d and len(d) == 8 else f"{nm} ({qd})"
                for nm, qd, d, _ in soc))
        elif e:
            P("- **Sócios (QSA):** nenhum registro no arquivo Socios (comum em empresário individual/MEI)")
    P("")

# ---------- CEIS / CNEP
from datetime import datetime


def dbr(x):
    try:
        return datetime.strptime(x, "%d/%m/%Y").date()
    except Exception:
        return None


if "ceis" in tabs:
    P("## CEIS / CNEP\n")
    P("Casamento pelo CNPJ do fornecedor (14 dígitos) ou pela raiz (8 dígitos, outro estabelecimento da mesma empresa). "
      "A coluna *Contrato com Belém no período* diz se algum contrato com Belém foi **assinado** entre o início e o fim "
      "da sanção. Isso só seria impeditivo se a abrangência da sanção alcançasse o município (por exemplo, inidoneidade "
      "ou \"todas as esferas\"); impedimento \"no órgão sancionador\" ou \"na esfera do sancionador\" federal, estadual ou de "
      "outro município não impede contratar com Belém.\n")
    for base in ("ceis", "cnep"):
        hits = q(f"""
            WITH s AS (SELECT *, regexp_replace(cpf_ou_cnpj_do_sancionado, '[^0-9A-Za-z]', '', 'g') AS doc FROM {base}),
                 f AS (SELECT fornecedor_ni, max(fornecedor_nome) nome, list(data_assinatura ORDER BY data_assinatura) ass,
                              count(*) n, sum(valor_global) FILTER (conta_no_valor) v
                         FROM contratos WHERE fornecedor_tipo = 'PJ' GROUP BY 1)
            SELECT DISTINCT f.fornecedor_ni, f.nome, s.doc, s.categoria_da_sancao, s.data_inicio_sancao,
                   s.data_final_sancao, s.orgao_sancionador, s.uf_orgao_sancionador, s.abragencia_da_sancao,
                   CASE WHEN s.doc = f.fornecedor_ni THEN 'CNPJ' ELSE 'raiz' END, f.ass, f.n, f.v
              FROM f JOIN s ON length(s.doc) = 14 AND substr(s.doc, 1, 8) = substr(f.fornecedor_ni, 1, 8)
             ORDER BY 2, 5""")
        fornecedores = sorted({h[0] for h in hits})
        P(f"**{base.upper()}** (arquivo de {q(f'SELECT max(arquivo_data) FROM {base}')[0][0]}): "
          f"{len(fornecedores)} fornecedor(es), {len(hits)} registro(s) de sanção\n")
        if hits:
            P("| Fornecedor | CNPJ | Casa por | Contratos com Belém (valor) | Categoria | Início | Fim | Órgão sancionador | Abrangência | Contrato com Belém no período |")
            P("|---|---|---|---|---|---|---|---|---|---|")
            for h in hits:
                ini, fim = dbr(h[4]), dbr(h[5])
                dentro = [d for d in h[10] if d and ini and d >= ini and (fim is None or d <= fim)]
                P(f"| {h[1]} | `{h[0]}` | {h[9]} | {h[11]} ({brl(h[12])}) | {h[3]} | {h[4]} | {h[5] or '—'} | "
                  f"{h[6]} ({h[7]}) | {h[8]} | {'**sim**: ' + ', '.join(f'{d:%d/%m/%Y}' for d in dentro) if dentro else 'não'} |")
        P("")
