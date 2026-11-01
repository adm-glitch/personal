import zipfile, json, collections, math, os, gzip, struct, sqlite3, unicodedata, base64, io

def vi(n,out):
    while True:
        b=n&0x7f; n>>=7
        out.append(b|0x80 if n else b)
        if not n: break
def zz(n): return (n<<1) if n>=0 else ((-n)<<1)-1
def viz(n,out): vi(zz(n),out)
def wstr(s,out):
    b=s.encode('utf-8'); vi(len(b),out); out.extend(b)

# ---------- bairro polygons ----------
def rings(blob):
    env=(blob[3]>>1)&0x07; off=8+{0:0,1:32,2:48,3:48,4:64}[env]
    w=blob[off:]; en='<' if w[0]==1 else '>'
    gt=struct.unpack(en+'I',w[1:5])[0]%1000; pos=5; out=[]
    def rd(pos):
        nr=struct.unpack(en+'I',w[pos:pos+4])[0]; pos+=4; rs=[]
        for _ in range(nr):
            npt=struct.unpack(en+'I',w[pos:pos+4])[0]; pos+=4
            v=struct.unpack(en+f'{npt*2}d',w[pos:pos+npt*16]); pos+=npt*16
            rs.append(list(zip(v[0::2],v[1::2])))
        return rs,pos
    if gt==3: r,pos=rd(pos); out.append(r)
    elif gt==6:
        nn=struct.unpack(en+'I',w[pos:pos+4])[0]; pos+=4
        for _ in range(nn): pos+=5; r,pos=rd(pos); out.append(r)
    return out
con=sqlite3.connect('PA_bairros.gpkg')
BA=[]
for nm,g in con.execute("select NM_BAIRRO, geom from PA_bairros_CD2022 where CD_MUN='1501402'"):
    polys=rings(g)
    xs=[p[0] for pl in polys for r in pl for p in r]; ys=[p[1] for pl in polys for r in pl for p in r]
    BA.append({'nm':nm,'polys':polys,'bb':(min(xs),min(ys),max(xs),max(ys))})
def pip(x,y,r):
    ins=False;n=len(r);j=n-1
    for i in range(n):
        xi,yi=r[i];xj,yj=r[j]
        if ((yi>y)!=(yj>y)) and x<(xj-xi)*(y-yi)/(yj-yi+1e-18)+xi: ins=not ins
        j=i
    return ins
def which(x,y):
    for bi,b in enumerate(BA):
        x0,y0,x1,y1=b['bb']
        if not(x0<=x<=x1 and y0<=y<=y1): continue
        for pl in b['polys']:
            if pip(x,y,pl[0]) and not any(pip(x,y,h) for h in pl[1:]): return bi
    return None

# ---------- source data ----------
zf=zipfile.ZipFile('PA_faces.zip')
rawf=json.loads(zf.open('PA/1501402_faces_de_logradouros_2022.json').read())['features']
named=[f for f in rawf if 'CD_QUADRA' in f['properties']]
unattr=[f for f in rawf if 'CD_QUADRA' not in f['properties']]
z=zipfile.ZipFile('belem_cnefe.json.zip')
res=[f for f in json.loads(z.open('qg_810_endereco_Munic1501402.json').read())['features']
     if f['properties']['COD_ESPECIE']=='1']
print("faces",len(named),"unattr",len(unattr),"addresses",len(res))

streets=[];smap={}
def si(n):
    if n not in smap: smap[n]=len(streets); streets.append(n)
    return smap[n]
QID={};Q=[]
def qid(setor,num):
    kk=(setor,int(num))
    if kk not in QID:
        QID[kk]=len(Q); Q.append({'setor':setor,'num':int(num),'geo':0,'pts':[],'apts':[]})
    return QID[kk]
for f in named: qid(f['properties']['CD_SETOR'],f['properties']['CD_QUADRA'])
for f in res:   qid(f['properties']['COD_SETOR'],f['properties']['NUM_QUADRA'])

F=[]; seenf=set()
for f in named:
    p=f['properties']; q=qid(p['CD_SETOR'],p['CD_QUADRA']); Q[q]['geo']=1
    nm=' '.join(x for x in [p['NM_TIP_LOG'],p['NM_TIT_LOG'],p['NM_LOG']] if x)
    g=[(round(c[0]*1e6),round(c[1]*1e6)) for c in f['geometry']['coordinates']]
    F.append({'q':q,'f':int(p['CD_FACE']),'s':si(nm),'r':int(p['TOT_RES'] or 0),'g':g})
    Q[q]['pts'].extend(g); seenf.add((q,int(p['CD_FACE'])))
A=[]
for f in res:
    p=f['properties']; q=qid(p['COD_SETOR'],p['NUM_QUADRA'])
    ln=p['LOGRAD_NUM']; st,_,num=ln.rpartition(', ')
    x=round(f['geometry']['coordinates'][0]*1e6); y=round(f['geometry']['coordinates'][1]*1e6)
    A.append({'x':x,'y':y,'s':si(st),'n':num.strip(),'c':p['COMPLEMENTO'].strip(),
              'q':q,'f':int(p['NUM_FACE'])})
    Q[q]['apts'].append((x,y))
ghost=collections.defaultdict(list)
for i,a in enumerate(A):
    if (a['q'],a['f']) not in seenf: ghost[(a['q'],a['f'])].append(i)
for (q,fn),ids in ghost.items():
    c=collections.Counter(A[i]['s'] for i in ids)
    F.append({'q':q,'f':fn,'s':c.most_common(1)[0][0],'r':len(ids),'g':[]})
print("ghost faces",len(ghost),"total faces",len(F),"quadras",len(Q))

# bairro per quadra
for q in Q:
    ps=q['apts'] or q['pts']
    q['b']=(which(ps[0][0]/1e6,ps[0][1]/1e6) if ps else None)
    if q['b'] is None:
        for p in ps[:20]:
            b=which(p[0]/1e6,p[1]/1e6)
            if b is not None: q['b']=b; break
usedb=sorted({q['b'] for q in Q if q['b'] is not None})
bmap={b:i for i,b in enumerate(usedb)}
NOB=len(usedb)
for q in Q: q['bi']= bmap.get(q['b'], NOB)
bnames=[BA[b]['nm'] for b in usedb]+['Sem bairro definido']
for q in Q:
    ps=q['pts'] or q['apts']
    q['c']=(sum(p[0] for p in ps)//len(ps), sum(p[1] for p in ps)//len(ps)) if ps else (0,0)
    q.pop('pts'); q.pop('apts')
print("bairros used:",NOB)

# ---------- pre-register road names so the dictionary is complete ----------
CLS={'motorway':0,'motorway_link':0,'trunk':1,'trunk_link':1,'primary':2,'primary_link':2,
     'secondary':3,'secondary_link':3,'tertiary':4,'tertiary_link':4,'residential':5,
     'unclassified':6,'living_street':6,'service':7,'pedestrian':8,'busway':3}
rd=json.load(open('osm_roads.json'))
RD=[e for e in rd['elements'] if e.get('geometry')]
for e in RD:
    if e['tags'].get('name'): si(e['tags']['name'])
print("street dictionary entries:",len(streets))

# ---------- encode ----------
out=bytearray()
out.extend(b'BLM3')
wstr('\n'.join(streets),out)
wstr('\n'.join(bnames),out)
# bairro polygons (outer rings, thinned)
polys=[]
for b in usedb:
    rs=[]
    for pl in BA[b]['polys']:
        r=[(round(p[0]*1e6),round(p[1]*1e6)) for p in pl[0][::3]]
        if len(r)>3: rs.append(r)
    polys.append(rs)
vi(len(polys),out)
for rs in polys:
    vi(len(rs),out)
    for r in rs:
        vi(len(r),out); px=py=0
        for x,y in r: viz(x-px,out); viz(y-py,out); px,py=x,y
# quadras
vi(len(Q),out); px=py=0
for q in Q:
    vi(q['bi'],out); vi(q['num'],out); out.append(q['geo'])
    wstr(q['setor'][-5:],out)
    viz(q['c'][0]-px,out); viz(q['c'][1]-py,out); px,py=q['c']
# faces (sorted by quadra for delta locality)
F.sort(key=lambda f:(f['q'],f['f']))
vi(len(F),out); pq=0
for f in F:
    viz(f['q']-pq,out); pq=f['q']
    vi(f['f'],out); vi(f['s'],out); vi(f['r'],out); vi(len(f['g']),out)
    px=py=0
    for x,y in f['g']: viz(x-px,out); viz(y-py,out); px,py=x,y
# addresses, columnar, sorted by quadra/face
A.sort(key=lambda a:(a['q'],a['f'],a['y']))
vi(len(A),out)
px=py=0
for a in A: viz(a['x']-px,out); viz(a['y']-py,out); px,py=a['x'],a['y']
pq=0
for a in A: viz(a['q']-pq,out); pq=a['q']
for a in A: vi(a['f'],out)
for a in A: vi(a['s'],out)
nb=bytearray(); cb=bytearray()
for a in A: wstr(a['n'],nb)
for a in A: wstr(a['c'],cb)
vi(len(nb),out); out.extend(nb)
vi(len(cb),out); out.extend(cb)
# roads
vi(len(RD),out)
for e in RD:
    t=e['tags']
    out.append(CLS.get(t.get('highway'),9))
    vi(si(t['name'])+1 if t.get('name') else 0,out)
    g=[(round(p['lon']*1e6),round(p['lat']*1e6)) for p in e['geometry']]
    vi(len(g),out); px=py=0
    for x,y in g: viz(x-px,out); viz(y-py,out); px,py=x,y
# duplicate-number bitset: same street+número in another quadra within 50 m
import math as _m
byp=collections.defaultdict(list)
for i,a in enumerate(A):
    if a['n'] in ('','SN','S/N'): continue
    byp[(a['s'],a['n'])].append(i)
dup=bytearray((len(A)+7)//8)
ndup=0
for _k,ids in byp.items():
    if len(ids)<2: continue
    qs={A[i]['q'] for i in ids}
    if len(qs)<2: continue
    for i in range(len(ids)):
        for j in range(i+1,len(ids)):
            a,b=A[ids[i]],A[ids[j]]
            if a['q']==b['q']: continue
            d=_m.hypot((a['x']-b['x'])/1e6*111320*0.9997,(a['y']-b['y'])/1e6*110574)
            if d<50:
                for t in (ids[i],ids[j]):
                    if not (dup[t>>3]>>(t&7))&1: ndup+=1
                    dup[t>>3]|=1<<(t&7)
print("addresses flagged as near-duplicate numbers:",ndup)
out.extend(dup)

vi(len(unattr),out)
for f in unattr:
    g=[(round(c[0]*1e6),round(c[1]*1e6)) for c in f['geometry']['coordinates']]
    vi(len(g),out); px=py=0
    for x,y in g: viz(x-px,out); viz(y-py,out); px,py=x,y
raw=bytes(out)
gz=gzip.compress(raw,9)
print(f"\nbinary {len(raw)/1024/1024:.2f} MB -> gzip {len(gz)/1024/1024:.2f} MB -> base64 {len(gz)*4/3/1024/1024:.2f} MB")
open('city.bin','wb').write(raw); open('city.bin.gz','wb').write(gz)
json.dump({'streets':len(streets),'quadras':len(Q),'faces':len(F),'addr':len(A),'roads':len(RD),'unattr':len(unattr),'bairros':len(bnames)},open('city.meta.json','w'))
