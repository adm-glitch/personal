"""Assemble an admin-panel HTML from parts/admin_shell.html + an admin payload.
Usage: python3 mockups/build_admin.py data/vigia.admin.json vigia_admin.html"""
import json, re, os, sys, collections
HERE=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(HERE)
src, out = sys.argv[1], sys.argv[2]
src = src if os.path.exists(src) else os.path.join(ROOT, src)
h=open(os.path.join(HERE,'parts','admin_shell.html'),encoding='utf-8').read()
fail=[]
ids=re.findall(r'(?<![-\w])id="([^"]+)"', h)
dup={k:v for k,v in collections.Counter(ids).items() if v>1}
if dup: fail.append(f"duplicate ids {dup}")
types={}
for m in re.finditer(r'<(\w+)[^>]*?(?<![-\w])id="([^"]+)"', h): types[m.group(2)]=m.group(1)
for u in set(re.findall(r"getElementById\(\'([^\']+)\'\)", h)):
    if u not in types: fail.append(f"missing id {u}")
if re.findall(r'(?:src|href)\s*=\s*["\']https?://', h): fail.append("external URL (blocked by CSP)")
if fail: print("CHECKS FAILED:", fail); raise SystemExit(1)
print("checks ok")
d=json.load(open(src)); muni=d.get('muni','Belém')
page=h.replace('<title>Mutirão Belém — painel de cobertura</title>',
               f'<title>Mutirão {muni} — painel de cobertura</title>')
page=page.replace('<h1 id="h1">Mutirão Belém</h1>', f'<h1 id="h1">Mutirão {muni}</h1>')
page=page.replace('/*__DATA__*/', open(src,encoding='utf-8').read())
open(out,'w',encoding='utf-8').write(page)
open(os.path.join(HERE,'harness','admin_main.js'),'w',encoding='utf-8').write(
    re.findall(r'<script>(.*?)</script>', h, re.S)[-1])
print(out, muni, round(os.path.getsize(out)/1024), 'KB')
