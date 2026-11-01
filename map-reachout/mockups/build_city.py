import base64, os, re
head=open('head.part',encoding='utf-8').read()
head=head.replace('Mockup v5 · dados reais · 6 bairros, 427 quadras','Mockup v6 · Belém inteira · dados reais')
i=head.find('<p class="lede">')
old=head[i:head.find('</p>',i)+4]
head=head.replace(old,'<p class="lede">The whole city, in the browser: <strong>528.686 domicílios</strong>, <strong>8.604 quadras</strong>, <strong>45.559 faces</strong>, <strong>71 bairros</strong> and <strong>27.476 ruas</strong> — shipped as one <strong>3,7 MB</strong> gzipped binary and decoded into typed arrays, which is exactly what the real app would do. Zoom in: bairros → quadras → ruas → números.</p>')
if 'id="zlvl"' not in head:
    head=head.replace('<span class="place">Belém/PA</span>','<span class="place">Belém/PA</span><span class="place" id="zlvl" style="margin-left:0;color:var(--focus)">bairros</span>')
head=head.replace('<button class="btn" id="fill">Preencher quadra 001</button>','<button class="btn" id="fill">Preencher a quadra</button>')
script=open('script.part',encoding='utf-8').read()
app=open('app.part',encoding='utf-8').read().replace('/*__UI__*/', open('ui.part',encoding='utf-8').read())
script=script.replace('/*__APP__*/', app)
# checks
fail=[]
import collections
ids=re.findall(r'(?<![-\w])id="([^"]+)"', head)
dup={k:v for k,v in collections.Counter(ids).items() if v>1}
if dup: fail.append(f"duplicate ids {dup}")
types={}
for m in re.finditer(r'<(\w+)[^>]*?(?<![-\w])id="([^"]+)"', head): types[m.group(2)]=m.group(1)
DYN={'blk','add-in','add-ok','add-cancel','add-place','add-unit','pick-x','pick-here','nextq','zlvl'}
for u in set(re.findall(r"getElementById\('([^']+)'\)", script)):
    if u not in types and u not in DYN: fail.append(f"missing id {u}")
if fail: print("CHECKS FAILED:",fail); raise SystemExit(1)
print("checks ok")
b64=base64.b64encode(open('city.bin.gz','rb').read()).decode()
open('mockup.html','w',encoding='utf-8').write(head+script.replace('/*__BLOCK__*/', b64))
open('mockup_main.js','w',encoding='utf-8').write(re.findall(r'<script>(.*?)</script>', script, re.S)[-1])
print("artifact:",round(os.path.getsize('mockup.html')/1024/1024,2),"MB")
