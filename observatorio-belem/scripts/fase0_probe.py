#!/usr/bin/env python3
"""Fase 0: sonda educada de uma URL, guardando o bruto e um meta.json.

Uso:
  python3 -I scripts/fase0_probe.py <fonte> <url> [--name arquivo] [--head] [--max-bytes N]
                                    [--header 'K: V'] [--data 'corpo POST'] [--insecure]

Grava em raw/<fonte>/<AAAA-MM-DD>/<arquivo> e acrescenta a entrada em raw/<fonte>/<AAAA-MM-DD>/meta.json
(URL, timestamp UTC, status, cabeçalhos, tempo, erro). Respeita >= 1 s entre requisições ao mesmo host
(estado em raw/.ratelimit.json). Só stdlib.
"""
import argparse, json, os, ssl, sys, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone

UA = "observatorio-belem/0.1 (pesquisa civica; contato via github adm-glitch)"
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
RL_FILE = os.path.join(ROOT, "raw", ".ratelimit.json")


def wait_host(host: str, gap: float = 1.1) -> None:
    try:
        with open(RL_FILE) as f:
            st = json.load(f)
    except Exception:
        st = {}
    last = st.get(host, 0)
    delta = time.time() - last
    if delta < gap:
        time.sleep(gap - delta)
    st[host] = time.time()
    os.makedirs(os.path.dirname(RL_FILE), exist_ok=True)
    with open(RL_FILE, "w") as f:
        json.dump(st, f)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("fonte")
    ap.add_argument("url")
    ap.add_argument("--name")
    ap.add_argument("--head", action="store_true")
    ap.add_argument("--max-bytes", type=int, default=5_000_000)
    ap.add_argument("--header", action="append", default=[])
    ap.add_argument("--data")
    ap.add_argument("--insecure", action="store_true")
    ap.add_argument("--timeout", type=float, default=30)
    a = ap.parse_args()

    host = urllib.parse.urlparse(a.url).hostname or ""
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    outdir = os.path.join(ROOT, "raw", a.fonte, day)
    os.makedirs(outdir, exist_ok=True)
    name = a.name or (urllib.parse.urlparse(a.url).path.strip("/").replace("/", "_") or "index")[:120]

    headers = {"User-Agent": UA, "Accept": "*/*"}
    for h in a.header:
        k, v = h.split(":", 1)
        headers[k.strip()] = v.strip()
    data = a.data.encode() if a.data is not None else None
    method = "HEAD" if a.head else ("POST" if data is not None else "GET")
    req = urllib.request.Request(a.url, headers=headers, data=data, method=method)
    ctx = ssl.create_default_context()
    if a.insecure:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

    wait_host(host)
    t0 = time.time()
    entry = {"url": a.url, "method": method, "fetched_at": datetime.now(timezone.utc).isoformat(),
             "user_agent": UA, "file": None, "insecure_tls": a.insecure}
    body = b""
    try:
        with urllib.request.urlopen(req, timeout=a.timeout, context=ctx) as r:
            entry["status"] = r.status
            entry["final_url"] = r.geturl()
            entry["headers"] = dict(r.headers.items())
            if not a.head:
                body = r.read(a.max_bytes)
    except urllib.error.HTTPError as e:
        entry["status"] = e.code
        entry["headers"] = dict(e.headers.items()) if e.headers else {}
        try:
            body = e.read(a.max_bytes)
        except Exception:
            pass
        entry["error"] = f"HTTPError {e.code} {e.reason}"
    except Exception as e:  # timeout, TLS, DNS
        entry["status"] = None
        entry["error"] = f"{type(e).__name__}: {e}"
    entry["elapsed_s"] = round(time.time() - t0, 2)
    if body:
        path = os.path.join(outdir, name)
        with open(path, "wb") as f:
            f.write(body)
        entry["file"] = name
        entry["bytes"] = len(body)
        entry["truncated"] = len(body) >= a.max_bytes

    meta_path = os.path.join(outdir, "meta.json")
    try:
        with open(meta_path) as f:
            meta = json.load(f)
    except Exception:
        meta = {"fonte": a.fonte, "probes": []}
    meta["probes"].append(entry)
    with open(meta_path, "w") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)

    ct = entry.get("headers", {}).get("Content-Type", "")
    print(f"{entry.get('status')} {entry['elapsed_s']}s {ct} {entry.get('bytes', 0)}B {entry.get('error', '')}")
    if body and not a.head:
        print(body[:600].decode("utf-8", "replace"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
