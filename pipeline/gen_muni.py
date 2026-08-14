"""Build the field payload (.bin.gz) and the admin aggregate for one municipality.
Falls back from the IBGE bairro mesh to CNEFE's DSC_LOCALIDADE when the
municipality has no official bairro division — most of Brazil does not."""
import zipfile, json, collections, math, os, gzip, struct, sqlite3, unicodedata, sys, random

MUN, NAME, CNEFE, ROADS, OUT = sys.argv[1:6]
random.seed(11)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
UFC  = {'11':'RO','12':'AC','13':'AM','14':'RR','15':'PA','16':'AP','17':'TO','21':'MA',
        '22':'PI','23':'CE','24':'RN','25':'PB','26':'PE','27':'AL','28':'SE','29':'BA',
        '31':'MG','32':'ES','33':'RJ','35':'SP','41':'PR','42':'SC','43':'RS','50':'MS',
        '51':'MT','52':'GO','53':'DF'}
UF   = UFC[MUN[:2]]
def d(*p): return os.path.join(DATA, *p)
def rel(p): return p if os.path.isabs(p) else (p if os.path.exists(p) else d(os.path.basename(p)))
CNEFE, ROADS = rel(CNEFE), rel(ROADS)
OUT = OUT if os.path.isabs(OUT) else d(os.path.basename(OUT))
def vi(n,o):
    while True:
        b=n&0x7f; n>>=7; o.append(b|0x80 if n else b)
        if not n: break
def zz(n): return (n<<1) if n>=0 else ((-n)<<1)-1
def viz(n,o): vi(zz(n),o)
def wstr(s,o):
    b=s.encode('utf-8'); vi(len(b),o); o.extend(b)
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
def pip(x,y,r):
    ins=False;n=len(r);j=n-1
    for i in range(n):
        xi,yi=r[i];xj,yj=r[j]
        if ((yi>y)!=(yj>y)) and x<(xj-xi)*(y-yi)/(yj-yi+1e-18)+xi: ins=not ins
        j=i
    return ins

# ---- bairro mesh, or fall back to locality names ----
con=sqlite3.connect(d(UF+'_bairros.gpkg'))
MESH=[]
for nm,g in con.execute(f"select NM_BAIRRO, geom from {UF}_bairros_CD2022 where CD_MUN=?", (MUN,)):
    polys=rings(g)
    xs=[p[0] for pl in polys for r in pl for p in r]; ys=[p[1] for pl in polys for r in pl for p in r]
    MESH.append({'nm':nm,'polys':polys,'bb':(min(xs),min(ys),max(xs),max(ys))})
USE_MESH=len(MESH)>0
BOUND=[]
if not USE_MESH:
    dcon=sqlite3.connect(d(UF+'_distritos.gpkg'))
    t=[r[0] for r in dcon.execute("select table_name from gpkg_contents")][0]
    for nm,g in dcon.execute(f"select NM_DIST, geom from '{t}' where CD_MUN=?", (MUN,)):
        for pl in rings(g): BOUND.append(pl[0])
print(f"{NAME}: bairro mesh = {'yes, '+str(len(MESH))+' bairros' if USE_MESH else 'NONE — falling back to DSC_LOCALIDADE'}"
      + (f"; {len(BOUND)} district rings" if BOUND else ""))
def which(x,y):
    for i,b in enumerate(MESH):
        x0,y0,x1,y1=b['bb']
        if not(x0<=x<=x1 and y0<=y<=y1): continue
        for pl in b['polys']:
            if pip(x,y,pl[0]) and not any(pip(x,y,h) for h in pl[1:]): return i
    return None

zf=zipfile.ZipFile(d(UF+'_faces.zip'))
rawf=json.loads(zf.open(f'{UF}/{MUN}_faces_de_logradouros_2022.json').read())['features']
named=[f for f in rawf if 'CD_QUADRA' in f['properties']]
unattr=[f for f in rawf if 'CD_QUADRA' not in f['properties']]
z=zipfile.ZipFile(CNEFE)
res=[f for f in json.loads(z.open(z.namelist()[0]).read())['features']
     if f['properties']['COD_ESPECIE']=='1']
print(f"  faces {len(named)} + {len(unattr)} unattributed | households {len(res)}")

streets=[];smap={}
def si(n):
    if n not in smap: smap[n]=len(streets); streets.append(n)
    return smap[n]
QID={};Q=[]
def qid(s,n):
    kk=(s,int(n))
    if kk not in QID: QID[kk]=len(Q); Q.append({'setor':s,'num':int(n),'geo':0,'pts':[],'apts':[],'len':0.0,'loc':collections.Counter()})
    return QID[kk]
def flen(g):
    return sum(math.hypot((g[i+1][0]-g[i][0])*111320*math.cos(math.radians(g[i][1])),(g[i+1][1]-g[i][1])*110574) for i in range(len(g)-1))
for f in named: qid(f['properties']['CD_SETOR'],f['properties']['CD_QUADRA'])
for f in res:   qid(f['properties']['COD_SETOR'],f['properties']['NUM_QUADRA'])
F=[];seen=set()
for f in named:
    p=f['properties']; q=qid(p['CD_SETOR'],p['CD_QUADRA']); Q[q]['geo']=1
    nm=' '.join(x for x in [p['NM_TIP_LOG'],p['NM_TIT_LOG'],p['NM_LOG']] if x)
    g=[(round(c[0]*1e6),round(c[1]*1e6)) for c in f['geometry']['coordinates']]
    F.append({'q':q,'f':int(p['CD_FACE']),'s':si(nm),'r':int(p['TOT_RES'] or 0),'g':g})
    Q[q]['pts'].extend(g); Q[q]['len']+=flen(f['geometry']['coordinates']); seen.add((q,int(p['CD_FACE'])))
A=[]
for f in res:
    p=f['properties']; q=qid(p['COD_SETOR'],p['NUM_QUADRA'])
    ln=p['LOGRAD_NUM']; st,_,num=ln.rpartition(', ')
    x=round(f['geometry']['coordinates'][0]*1e6); y=round(f['geometry']['coordinates'][1]*1e6)
    A.append({'x':x,'y':y,'s':si(st),'n':num.strip(),'c':p['COMPLEMENTO'].strip(),'q':q,'f':int(p['NUM_FACE'])})
    Q[q]['apts'].append((x,y)); Q[q]['loc'][p['DSC_LOCALIDADE']]+=1
ghost=collections.defaultdict(list)
for i,a in enumerate(A):
    if (a['q'],a['f']) not in seen: ghost[(a['q'],a['f'])].append(i)
for (q,fn),ids in ghost.items():
    c=collections.Counter(A[i]['s'] for i in ids)
    F.append({'q':q,'f':fn,'s':c.most_common(1)[0][0],'r':len(ids),'g':[]})
print(f"  ghost faces {len(ghost)} | quadras {len(Q)}")

bairros=[];bmap={}
def bi(n):
    if n not in bmap: bmap[n]=len(bairros); bairros.append(n)
    return bmap[n]
for q in Q:
    if USE_MESH:
        ps=q['apts'] or q['pts']; b=None
        for p in ps[:25]:
            b=which(p[0]/1e6,p[1]/1e6)
            if b is not None: break
        q['bi']=bi(MESH[b]['nm'] if b is not None else 'Sem bairro definido')
    else:
        q['bi']=bi(q['loc'].most_common(1)[0][0].title() if q['loc'] else 'Sem localidade')
    ps=q['pts'] or q['apts']
    q['c']=(sum(p[0] for p in ps)//len(ps), sum(p[1] for p in ps)//len(ps)) if ps else (0,0)
print(f"  top-level units: {len(bairros)}")

out=bytearray(); out.extend(b'BLM3')
CLS={'motorway':0,'motorway_link':0,'trunk':1,'trunk_link':1,'primary':2,'primary_link':2,
     'secondary':3,'secondary_link':3,'tertiary':4,'tertiary_link':4,'residential':5,
     'unclassified':6,'living_street':6,'service':7,'pedestrian':8,'busway':3}
rd=json.load(open(ROADS)); RD=[e for e in rd['elements'] if e.get('geometry')]
for e in RD:
    if e['tags'].get('name'): si(e['tags']['name'])
wstr('\n'.join(streets),out); wstr('\n'.join(bairros),out)
POLY=[]
if USE_MESH:
    for nm in bairros:
        m=next((x for x in MESH if x['nm']==nm),None)
        POLY.append([[(round(p[0]*1e6),round(p[1]*1e6)) for p in pl[0][::3]] for pl in m['polys'] if len(pl[0])>8] if m else [])
else:
    POLY=[[] for _ in bairros]
    POLY.append([[(round(p[0]*1e6),round(p[1]*1e6)) for p in r[::3]] for r in BOUND if len(r)>8])
vi(len(POLY),out)
for rs in POLY:
    vi(len(rs),out)
    for r in rs:
        vi(len(r),out); px=py=0
        for x,y in r: viz(x-px,out); viz(y-py,out); px,py=x,y
vi(len(Q),out); px=py=0
for q in Q:
    vi(q['bi'],out); vi(q['num'],out); out.append(q['geo']); wstr(q['setor'][-5:],out)
    viz(q['c'][0]-px,out); viz(q['c'][1]-py,out); px,py=q['c']
F.sort(key=lambda f:(f['q'],f['f']))
vi(len(F),out); pq=0
for f in F:
    viz(f['q']-pq,out); pq=f['q']
    vi(f['f'],out); vi(f['s'],out); vi(f['r'],out); vi(len(f['g']),out)
    px=py=0
    for x,y in f['g']: viz(x-px,out); viz(y-py,out); px,py=x,y
A.sort(key=lambda a:(a['q'],a['f'],a['y']))
vi(len(A),out); px=py=0
for a in A: viz(a['x']-px,out); viz(a['y']-py,out); px,py=a['x'],a['y']
pq=0
for a in A: viz(a['q']-pq,out); pq=a['q']
for a in A: vi(a['f'],out)
for a in A: vi(a['s'],out)
nb=bytearray(); cb=bytearray()
for a in A: wstr(a['n'],nb)
for a in A: wstr(a['c'],cb)
vi(len(nb),out); out.extend(nb); vi(len(cb),out); out.extend(cb)
vi(len(RD),out)
for e in RD:
    t=e['tags']; out.append(CLS.get(t.get('highway'),9))
    vi(si(t['name'])+1 if t.get('name') else 0,out)
    g=[(round(p['lon']*1e6),round(p['lat']*1e6)) for p in e['geometry']]
    vi(len(g),out); px=py=0
    for x,y in g: viz(x-px,out); viz(y-py,out); px,py=x,y
byp=collections.defaultdict(list)
for i,a in enumerate(A):
    if a['n'] not in ('','SN','S/N'): byp[(a['s'],a['n'])].append(i)
dup=bytearray((len(A)+7)//8); nd=0
for _k,ids in byp.items():
    if len(ids)<2: continue
    if len({A[i]['q'] for i in ids})<2: continue
    for i in range(len(ids)):
        for j in range(i+1,len(ids)):
            a,b=A[ids[i]],A[ids[j]]
            if a['q']==b['q']: continue
            if math.hypot((a['x']-b['x'])/1e6*111320*0.9997,(a['y']-b['y'])/1e6*110574)<50:
                for t in (ids[i],ids[j]):
                    if not (dup[t>>3]>>(t&7))&1: nd+=1
                    dup[t>>3]|=1<<(t&7)
out.extend(dup)
vi(len(unattr),out)
for f in unattr:
    g=[(round(c[0]*1e6),round(c[1]*1e6)) for c in f['geometry']['coordinates']]
    vi(len(g),out); px=py=0
    for x,y in g: viz(x-px,out); viz(y-py,out); px,py=x,y
raw=bytes(out); gz=gzip.compress(raw,9)
open(OUT+'.bin.gz','wb').write(gz)
print(f"  field payload: {len(raw)/1024/1024:.2f} MB -> gzip {len(gz)/1024:.0f} KB -> base64 {len(gz)*4/3/1024:.0f} KB | dup flags {nd}")

# ---------- admin aggregate ----------
def hull(pts):
    pts=sorted(set(pts))
    if len(pts)<3: return pts
    cr=lambda o,a,b:(a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    lo=[];up=[]
    for p in pts:
        while len(lo)>=2 and cr(lo[-2],lo[-1],p)<=0: lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up)>=2 and cr(up[-2],up[-1],p)<=0: up.pop()
        up.append(p)
    return lo[:-1]+up[:-1]
hhOf=collections.Counter()
for a in A: hhOf[a['q']]+=1
AQ=[]
for i,q in enumerate(Q):
    h=hull(q['pts']) if len(q['pts'])>=3 else []
    AQ.append({'h':[list(p) for p in h],'c':list(q['c']),'hh':hhOf[i],'len':round(q['len']),
               'b':q['bi'],'geo':q['geo'],'num':q['num'],'setor':q['setor'][-5:]})
tot=collections.Counter()
for q in AQ:
    p=max(0.0,min(0.95,random.uniform(0.05,0.95)*(1.25 if q['hh']>40 else 0.7)))
    reach=int(q['hh']*p); talked=int(reach*random.uniform(0.38,0.7)); rest=reach-talked
    au=int(rest*0.6); rc=int(rest*0.18); ix=int(rest*0.12)
    q['s']=[talked,au,rc,ix,max(0,rest-au-rc-ix)]
    for i,v in enumerate(q['s']): tot[i]+=v
BB=[]
if USE_MESH:
    for bidx,nm in enumerate(bairros):
        m=next((x for x in MESH if x['nm']==nm),None)
        if not m: continue
        g=[[[round(p[0]*1e6),round(p[1]*1e6)] for p in pl[0][::3]] for pl in m['polys'] if len(pl[0])>8]
        if g: BB.append({'b':bidx,'g':g})
else:
    g=[[[round(p[0]*1e6),round(p[1]*1e6)] for p in r[::3]] for r in BOUND if len(r)>8]
    if g: BB.append({'b':len(bairros),'g':g})
days=[int(sum(tot.values())*((d+1)/21)**1.35) for d in range(21)]
NAMES=['Rai','Dhara','Iracema','Benedito','Maruan','Cleide','Josivaldo','Nayara','Ubiratã','Sâmia','Reginaldo','Tainá']
crew=[]
for n in NAMES:
    d=int(random.uniform(180,900)); crew.append({'n':n,'d':d,'c':int(d*random.uniform(0.4,0.68)),'q':int(random.uniform(2,14))})
crew.sort(key=lambda c:-c['d'])
json.dump({'b':bairros+([] if USE_MESH else ['(divisa do município)']),'bb':BB,'q':AQ,'days':days,'crew':crew,
           'muni':NAME,'mesh':USE_MESH},open(OUT+'.admin.json','w'),separators=(',',':'))
print(f"  admin: {os.path.getsize(OUT+'.admin.json')/1024:.0f} KB | reached {sum(tot.values()):,} of {sum(q['hh'] for q in AQ):,}")
