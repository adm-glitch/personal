#!/usr/bin/env python3
"""Fase 1: base CNPJ da Receita filtrada pelos fornecedores do PNCP + CEIS/CNEP.

Uso:
  .venv/bin/python scripts/cnpj_filter.py cnpj   [--month 2026-10] [--only Empresas0,Socios3,...]
  .venv/bin/python scripts/cnpj_filter.py sancoes [--date AAAAMMDD]
  .venv/bin/python scripts/cnpj_filter.py load

cnpj:    lê do DuckDB os CNPJs básicos (8 dígitos) dos fornecedores PJ da tabela contratos e dos órgãos; baixa do
         Nextcloud da Receita (share público, WebDAV) UM ZIP POR VEZ, lê o CSV dentro do ZIP em fluxo (sem extrair),
         guarda só as linhas cujo CNPJ básico está no conjunto em data/staging/cnpj/<arquivo>.parquet e apaga o ZIP.
         Retomável: um arquivo com parquet pronto é pulado.
sancoes: baixa os CSVs diários do CEIS e do CNEP (download sem chave do Portal da Transparência) para
         raw/cgu/<data>/ e grava em data/staging/sancoes/.
load:    (re)cria no DuckDB as tabelas empresas, estabelecimentos, socios, simples, cnaes, motivos, municipios,
         naturezas, paises, qualificacoes, ceis, cnep a partir do staging.

CSV da Receita: sem cabeçalho, ';', aspas, latin-1. O CNPJ é tratado como texto (CNPJ alfanumérico desde 2026).
LGPD: o CPF mascarado do sócio PF (cpf_cnpj_socio) fica só na base interna, como chave; nunca vai para relatório.
"""
import argparse, csv, io, json, os, re, sys, time, zipfile
from datetime import date, datetime, timedelta, timezone

import httpx

UA = "observatorio-belem/0.1 (pesquisa civica; contato via github adm-glitch)"
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DB = os.path.join(ROOT, "data", "observatorio.duckdb")
STAGE = os.path.join(ROOT, "data", "staging")
TMP = os.path.join(ROOT, "data", "tmp")
SHARE = "gn672Ad4CF8N6TK"
WEBDAV = "https://arquivos.receitafederal.gov.br/public.php/webdav/Dados/Cadastros/CNPJ"

LAYOUT = {
    "Empresas": ["cnpj_basico", "razao_social", "natureza_juridica", "qualificacao_responsavel", "capital_social",
                 "porte_empresa", "ente_federativo_responsavel"],
    "Estabelecimentos": ["cnpj_basico", "cnpj_ordem", "cnpj_dv", "identificador_matriz_filial", "nome_fantasia",
                         "situacao_cadastral", "data_situacao_cadastral", "motivo_situacao_cadastral",
                         "nome_cidade_exterior", "pais", "data_inicio_atividade", "cnae_fiscal_principal",
                         "cnae_fiscal_secundaria", "tipo_logradouro", "logradouro", "numero", "complemento", "bairro",
                         "cep", "uf", "municipio", "ddd_1", "telefone_1", "ddd_2", "telefone_2", "ddd_fax", "fax",
                         "correio_eletronico", "situacao_especial", "data_situacao_especial"],
    "Socios": ["cnpj_basico", "identificador_socio", "nome_socio_razao_social", "cpf_cnpj_socio", "qualificacao_socio",
               "data_entrada_sociedade", "pais", "representante_legal", "nome_do_representante",
               "qualificacao_representante_legal", "faixa_etaria"],
    "Simples": ["cnpj_basico", "opcao_pelo_simples", "data_opcao_simples", "data_exclusao_simples", "opcao_mei",
                "data_opcao_mei", "data_exclusao_mei"],
}
DOMINIOS = ["Cnaes", "Motivos", "Municipios", "Naturezas", "Paises", "Qualificacoes"]
FILES = ([f"Empresas{i}" for i in range(10)] + [f"Estabelecimentos{i}" for i in range(10)] +
         [f"Socios{i}" for i in range(10)] + ["Simples"] + DOMINIOS)


def kind(name: str) -> str:
    return name.rstrip("0123456789")


def basicos_alvo() -> set[str]:
    import duckdb
    for _ in range(30):
        try:
            con = duckdb.connect(DB, read_only=True)
            break
        except duckdb.IOException:
            time.sleep(10)
    else:
        raise SystemExit("DuckDB ocupado")
    rows = con.execute("""
        SELECT DISTINCT substr(fornecedor_ni, 1, 8) FROM contratos
         WHERE fornecedor_tipo = 'PJ' AND length(fornecedor_ni) = 14
        UNION SELECT DISTINCT substr(cnpj, 1, 8) FROM orgaos""").fetchall()
    con.close()
    return {r[0] for r in rows}


def download(url: str, dest: str, auth=None):
    """Download em fluxo com retomada por Range e espera crescente."""
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    part = dest + ".part"
    for attempt in range(6):
        have = os.path.getsize(part) if os.path.exists(part) else 0
        headers = {"User-Agent": UA}
        if have:
            headers["Range"] = f"bytes={have}-"
        try:
            with httpx.stream("GET", url, headers=headers, auth=auth, timeout=httpx.Timeout(120, connect=30),
                              follow_redirects=True) as r:
                if r.status_code == 416:
                    break
                if 400 <= r.status_code < 500:
                    raise SystemExit(f"HTTP {r.status_code}: {url}")
                r.raise_for_status()
                mode = "ab" if have and r.status_code == 206 else "wb"
                with open(part, mode) as f:
                    for chunk in r.iter_bytes(1 << 20):
                        f.write(chunk)
            break
        except SystemExit:
            raise
        except Exception as e:
            print(f"  download falhou ({type(e).__name__}: {e}); nova tentativa {attempt + 1}", file=sys.stderr)
            time.sleep([5, 15, 45, 120, 240, 300][attempt])
    else:
        raise SystemExit(f"download falhou de vez: {url}")
    os.replace(part, dest)
    time.sleep(1.1)


# Naturezas jurídicas de entes/órgãos municipais (tabela Naturezas da Receita) + empresas públicas, sociedades de
# economia mista e consórcios públicos: usadas para levantar TODAS as entidades públicas municipais de Belém
# (verificação de completude), não só as que aparecem no PNCP.
NAT_PUBLICAS = {"1031", "1066", "1120", "1155", "1180", "1210", "1228", "1244", "1279", "1309", "1333", "2011", "2038"}
NAT_RE = re.compile(rb'^"[^"]*";"[^"]*";"(' + b"|".join(n.encode() for n in sorted(NAT_PUBLICAS)) + rb')";')


def filter_zip(zpath: str, cols: list[str], alvo: set[str] | None, natureza: bool = False):
    """Lê o(s) CSV(s) do ZIP em fluxo; devolve as linhas (listas) cujo cnpj_basico está em alvo (ou todas).
    natureza=True (Empresas): também guarda as empresas com natureza jurídica pública municipal (NAT_PUBLICAS)."""
    alvo_b = {f'"{b}"'.encode() for b in alvo} if alvo is not None else None
    out, n = [], 0
    with zipfile.ZipFile(zpath) as z:
        for info in z.infolist():
            with z.open(info) as fh:
                for line in fh:
                    n += 1
                    if alvo_b is not None and line[:10] not in alvo_b and not (natureza and NAT_RE.match(line)):
                        continue
                    row = next(csv.reader([line.decode("latin-1").rstrip("\r\n")], delimiter=";", quotechar='"'))
                    if len(row) != len(cols):
                        row = (row + [None] * len(cols))[:len(cols)]
                    out.append(row)
    return out, n


def basicos_publicos() -> set[str]:
    """CNPJs básicos com natureza pública guardados no staging de Empresas (para filtrar Estabelecimentos)."""
    import duckdb
    sd = os.path.join(STAGE, "cnpj")
    files = [os.path.join(sd, f) for f in os.listdir(sd) if f.startswith("Empresas") and f.endswith(".parquet")]
    if len(files) < 10:
        raise SystemExit("Empresas0-9 precisam estar prontos antes de Estabelecimentos")
    lst = "[" + ",".join(f"'{f}'" for f in files) + "]"
    nats = ",".join(f"'{n}'" for n in NAT_PUBLICAS)
    con = duckdb.connect()
    rows = con.execute(f"SELECT DISTINCT cnpj_basico FROM read_parquet({lst}) WHERE natureza_juridica IN ({nats})").fetchall()
    con.close()
    return {r[0] for r in rows}


def write_parquet(rows, cols, path):
    import duckdb
    os.makedirs(os.path.dirname(path), exist_ok=True)
    con = duckdb.connect()
    con.execute("CREATE TABLE t (" + ", ".join(f'"{c}" VARCHAR' for c in cols) + ")")
    if rows:
        con.executemany("INSERT INTO t VALUES (" + ",".join("?" * len(cols)) + ")", rows)
    con.execute(f"COPY t TO '{path}.tmp' (FORMAT parquet)")
    con.close()
    os.replace(path + ".tmp", path)


def cmd_cnpj(month: str, only: list[str] | None):
    alvo = basicos_alvo()
    print(f"{len(alvo)} CNPJs básicos-alvo (fornecedores PJ + órgãos)")
    with open(os.path.join(STAGE, "cnpj_alvo.json") if os.path.isdir(STAGE) else os.devnull, "w") as f:
        json.dump(sorted(alvo), f)
    log_path = os.path.join(STAGE, "cnpj", "log.jsonl")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    pub = None
    for name in FILES:
        if only and name not in only:
            continue
        out = os.path.join(STAGE, "cnpj", f"{name}.parquet")
        if os.path.exists(out):
            continue
        k = kind(name)
        cols = LAYOUT.get(k, ["codigo", "descricao"])
        zpath = os.path.join(TMP, f"{name}.zip")
        t0 = time.time()
        if not os.path.exists(zpath):
            download(f"{WEBDAV}/{month}/{name}.zip", zpath, auth=(SHARE, ""))
        zsize = os.path.getsize(zpath)
        t1 = time.time()
        if k == "Estabelecimentos" and pub is None:
            pub = basicos_publicos()
            print(f"  + {len(pub)} CNPJs básicos de natureza pública (para a lista de entidades municipais)")
        filtro = (alvo | pub) if k == "Estabelecimentos" else alvo
        rows, n = filter_zip(zpath, cols, filtro if k in LAYOUT else None, natureza=(k == "Empresas"))
        write_parquet(rows, cols, out)
        os.remove(zpath)
        entry = {"file": f"{name}.zip", "month": month, "zip_bytes": zsize, "lines_read": n, "rows_kept": len(rows),
                 "download_s": round(t1 - t0), "filter_s": round(time.time() - t1),
                 "at": datetime.now(timezone.utc).isoformat(), "url": f"{WEBDAV}/{month}/{name}.zip"}
        with open(log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")
        print(f"  {name}: {zsize/1e6:.0f} MB, {n} linhas, {len(rows)} mantidas "
              f"({entry['download_s']}s download, {entry['filter_s']}s filtro)", flush=True)


def cmd_sancoes(day: str | None):
    for base in ("ceis", "cnep"):
        d0 = datetime.strptime(day, "%Y%m%d").date() if day else datetime.now(timezone.utc).date()
        for back in range(0, 6):
            d = (d0 - timedelta(days=back)).strftime("%Y%m%d")
            outdir = os.path.join(ROOT, "raw", "cgu", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
            zpath = os.path.join(outdir, f"{d}_{base.upper()}.zip")
            url = f"https://portaldatransparencia.gov.br/download-de-dados/{base}/{d}"
            if not os.path.exists(zpath):
                try:
                    download(url, zpath)
                except SystemExit:
                    continue
            try:
                z = zipfile.ZipFile(zpath)
            except zipfile.BadZipFile:
                os.remove(zpath)
                continue
            name = z.namelist()[0]
            text = z.read(name).decode("latin-1")
            rd = csv.reader(io.StringIO(text), delimiter=";", quotechar='"')
            header = next(rd)
            cols = [norm(h) for h in header] + ["arquivo_data"]
            rows = [r + [d] for r in rd if r]
            write_parquet(rows, cols, os.path.join(STAGE, "sancoes", f"{base}.parquet"))
            with open(os.path.join(outdir, "meta.json"), "a") as f:
                f.write(json.dumps({"url": url, "file": os.path.basename(zpath), "csv": name, "rows": len(rows),
                                    "at": datetime.now(timezone.utc).isoformat()}) + "\n")
            print(f"  {base}: {d} {len(rows)} linhas")
            break
        else:
            print(f"  {base}: nenhum arquivo nos últimos 6 dias", file=sys.stderr)


def norm(h: str) -> str:
    import unicodedata
    h = unicodedata.normalize("NFKD", h).encode("ascii", "ignore").decode().lower()
    return "_".join("".join(ch if ch.isalnum() else " " for ch in h).split())


def cmd_load():
    import duckdb
    con = duckdb.connect(DB)
    sd = os.path.join(STAGE, "cnpj")
    for k in list(LAYOUT) + DOMINIOS:
        files = sorted(f for f in os.listdir(sd) if f.endswith(".parquet") and kind(f[:-8]) == k)
        if not files:
            print(f"  {k}: sem staging")
            continue
        lst = "[" + ",".join(f"'{os.path.join(sd, f)}'" for f in files) + "]"
        t = k.lower()
        if k == "Empresas":
            sel = ("cnpj_basico, razao_social, natureza_juridica, qualificacao_responsavel, "
                   "TRY_CAST(replace(capital_social, ',', '.') AS DOUBLE) AS capital_social, porte_empresa, "
                   "ente_federativo_responsavel")
        elif k == "Estabelecimentos":
            sel = ("cnpj_basico || cnpj_ordem || cnpj_dv AS cnpj, *, "
                   "TRY_STRPTIME(nullif(data_inicio_atividade, '0'), '%Y%m%d')::DATE AS data_abertura")
        else:
            sel = "*"
        con.execute(f"CREATE OR REPLACE TABLE {t} AS SELECT DISTINCT {sel} FROM read_parquet({lst})")
        print(f"  {t}: {con.execute(f'SELECT count(*) FROM {t}').fetchone()[0]}")
    for base in ("ceis", "cnep"):
        p = os.path.join(STAGE, "sancoes", f"{base}.parquet")
        if os.path.exists(p):
            con.execute(f"CREATE OR REPLACE TABLE {base} AS SELECT * FROM read_parquet('{p}')")
            print(f"  {base}: {con.execute(f'SELECT count(*) FROM {base}').fetchone()[0]}")
    meta = os.path.join(sd, "log.jsonl")
    if os.path.exists(meta):
        con.execute(f"CREATE OR REPLACE TABLE cnpj_carga AS SELECT * FROM read_json_auto('{meta}')")
    con.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["cnpj", "sancoes", "load"])
    ap.add_argument("--month", default="2026-10")
    ap.add_argument("--only")
    ap.add_argument("--date")
    a = ap.parse_args()
    os.makedirs(STAGE, exist_ok=True)
    if a.cmd == "cnpj":
        cmd_cnpj(a.month, a.only.split(",") if a.only else None)
    elif a.cmd == "sancoes":
        cmd_sancoes(a.date)
    else:
        cmd_load()


if __name__ == "__main__":
    main()
