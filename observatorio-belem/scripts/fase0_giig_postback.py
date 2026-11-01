#!/usr/bin/env python3
"""Fase 0: prova de raspagem do GIIG (Lexsom, ASP.NET WebForms) com um único postback.

Uso:
  python3 -I scripts/fase0_giig_postback.py <fonte> <url_da_consulta> <dd/mm/aaaa_inicio> <dd/mm/aaaa_fim>

GET na página (pega __VIEWSTATE/__EVENTVALIDATION), espera 1,1 s, POST com o intervalo de datas e o botão
"Buscar". Grava GET e POST em raw/<fonte>/<data>/ com meta.json. Uma consulta, sem paginação.
"""
import html, json, os, re, sys, time, urllib.parse, urllib.request, http.cookiejar
from datetime import datetime, timezone

UA = "observatorio-belem/0.1 (pesquisa civica; contato via github adm-glitch)"
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def main() -> int:
    fonte, url, ini, fim = sys.argv[1:5]
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out = os.path.join(ROOT, "raw", fonte, day)
    os.makedirs(out, exist_ok=True)
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.addheaders = [("User-Agent", UA)]

    t = datetime.now(timezone.utc).isoformat()
    page = op.open(url, timeout=40).read().decode("utf-8", "replace")
    open(os.path.join(out, "postback_get.html"), "w").write(page)

    form = {}
    for m in re.finditer(r'<input[^>]*type="hidden"[^>]*>', page):
        n = re.search(r'name="([^"]+)"', m.group(0))
        v = re.search(r'value="([^"]*)"', m.group(0))
        if n:
            form[n.group(1)] = html.unescape(v.group(1)) if v else ""
    for sel in re.findall(r'<select[^>]*name="([^"]+)"', page):
        form[sel] = ""  # "Todos......" costuma ter value vazio; ajustado abaixo
        opt = re.search(r'<select[^>]*name="%s"[^>]*>\s*<option[^>]*value="([^"]*)"' % re.escape(sel), page)
        if opt:
            form[sel] = opt.group(1)
    names = re.findall(r'name="([^"]+txtData)"', page)
    if len(names) >= 2:
        form[names[0]] = ini
        form[names[1]] = fim
    btn = next((n for n in re.findall(r'name="([^"]+)"', page) if n.endswith("btnbuscar")), None)
    if btn:
        form[btn] = "Buscar"
    time.sleep(1.1)
    t2 = datetime.now(timezone.utc).isoformat()
    req = urllib.request.Request(url, data=urllib.parse.urlencode(form).encode(),
                                 headers={"Content-Type": "application/x-www-form-urlencoded", "Referer": url})
    r = op.open(req, timeout=90)
    body = r.read(5_000_000).decode("utf-8", "replace")
    open(os.path.join(out, "postback_post.html"), "w").write(body)
    meta_path = os.path.join(out, "meta.json")
    try:
        meta = json.load(open(meta_path))
    except Exception:
        meta = {"fonte": fonte, "probes": []}
    meta["probes"] += [
        {"url": url, "method": "GET", "fetched_at": t, "file": "postback_get.html", "user_agent": UA},
        {"url": url, "method": "POST", "fetched_at": t2, "file": "postback_post.html", "status": r.status,
         "form_fields": sorted(form.keys()), "periodo": [ini, fim], "user_agent": UA},
    ]
    json.dump(meta, open(meta_path, "w"), ensure_ascii=False, indent=1)
    txt = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>", "", body, flags=re.S))))
    print(r.status, len(body), "bytes")
    i = txt.find("Empenh")
    print(txt[i:i + 1500])
    return 0


if __name__ == "__main__":
    sys.exit(main())
