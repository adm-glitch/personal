import base64, os, re, sys, collections, json
HERE = os.path.dirname(os.path.abspath(__file__))
PARTS = os.path.join(HERE, 'parts')
ROOT = os.path.dirname(HERE)
def part(n): return os.path.join(PARTS, n)
prefix, muni, nblab, outfile, lede, eyebrow = sys.argv[1:7]
head=open(part('head.part'),encoding='utf-8').read()
head=re.sub(r'<p class="eyebrow">[^<]*</p>', '<p class="eyebrow">'+eyebrow+'</p>', head, count=1)
i=head.find('<p class="lede">'); head=head[:i]+'<p class="lede">'+lede+'</p>'+head[head.find('</p>',i)+4:]
head=re.sub(r'<h1>[^<]*</h1>', '<h1>'+muni+' — app de campo</h1>', head, count=1)
head=head.replace('<title>Mutirão — app mockup, Terra Firme</title>', '<title>'+muni+' — app de campo</title>')
head=re.sub(r'<span class="place">[^<]*</span>', '<span class="place">'+muni+'/PA</span>', head, count=1)
# drop the Belém-specific analysis sections
for marker in ['<section>\n  <h2>Números repetidos','<section>\n  <h2>How far apart','<section>\n  <h2>The holes, citywide']:
    while marker in head:
        s=head.find(marker); e=head.find('</section>',s)+len('</section>')
        head=head[:s]+head[e:]
gz=open(prefix+'.bin.gz' if os.path.exists(prefix+'.bin.gz') else os.path.join(ROOT,'data',os.path.basename(prefix)+'.bin.gz'),'rb').read()
script=open(part('script.part'),encoding='utf-8').read()
app=open(part('app.part'),encoding='utf-8').read().replace('/*__UI__*/', open(part('ui.part'),encoding='utf-8').read())
script=script.replace('/*__APP__*/', app)
script=script.replace('__MUNI__',muni).replace('__NBLAB__',nblab).replace('__MAPMB__',f'{len(gz)/1024:.0f} KB')
fail=[]
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
open(outfile,'w',encoding='utf-8').write(head+script.replace('/*__BLOCK__*/', base64.b64encode(gz).decode()))
open(os.path.join(HERE,'harness','muni_main.js'),'w',encoding='utf-8').write(re.findall(r'<script>(.*?)</script>', script, re.S)[-1])
print(outfile+":", round(os.path.getsize(outfile)/1024),"KB")
