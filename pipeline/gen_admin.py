import zipfile, json, collections, math, os, gzip, sqlite3, struct, random, unicodedata
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def d(*p): return os.path.join(ROOT,'data',*p)
random.seed(7)
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
con=sqlite3.connect(d('PA_bairros.gpkg'))
BA=[]
for nm,g in con.execute("select NM_BAIRRO, geom from PA_bairros_CD2022 where CD_MUN='1501402'"):
    polys=rings(g)
    xs=[p[0] for pl in polys for r in pl for p in r]; ys=[p[1] for pl in polys for r in pl for p in r]
    BA.append({'nm':nm,'polys':polys,'bb':(min(xs),min(ys),max(xs),max(ys))})
def which(x,y):
    for bi,b in enumerate(BA):
        x0,y0,x1,y1=b['bb']
        if not(x0<=x<=x1 and y0<=y<=y1): continue
        for pl in b['polys']:
            if pip(x,y,pl[0]) and not any(pip(x,y,h) for h in pl[1:]): return bi
    return None

zf=zipfile.ZipFile(d('PA_faces.zip'))
faces=[f for f in json.loads(zf.open('PA/1501402_faces_de_logradouros_2022.json').read())['features'] if 'CD_QUADRA' in f['properties']]
z=zipfile.ZipFile(d('cnefe_1501402.json.zip'))
res=[f for f in json.loads(z.open('qg_810_endereco_Munic1501402.json').read())['features']
     if f['properties']['COD_ESPECIE']=='1']
QID={};Q=[]
def qid(s,n):
    kk=(s,int(n))
    if kk not in QID: QID[kk]=len(Q); Q.append({'pts':[],'apts':[],'hh':0,'len':0.0,'setor':s,'num':int(n)})
    return QID[kk]
def flen(g):
    return sum(math.hypot((g[i+1][0]-g[i][0])*111320*math.cos(math.radians(g[i][1])),(g[i+1][1]-g[i][1])*110574) for i in range(len(g)-1))
for f in faces:
    p=f['properties']; q=qid(p['CD_SETOR'],p['CD_QUADRA'])
    g=f['geometry']['coordinates']
    Q[q]['pts'].extend([(round(c[0]*1e6),round(c[1]*1e6)) for c in g])
    Q[q]['len']+=flen(g)
for f in res:
    p=f['properties']; q=qid(p['COD_SETOR'],p['NUM_QUADRA'])
    c=f['geometry']['coordinates']
    Q[q]['apts'].append((round(c[0]*1e6),round(c[1]*1e6))); Q[q]['hh']+=1
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
bairros=[];bmap={}
def bi(n):
    if n not in bmap: bmap[n]=len(bairros); bairros.append(n)
    return bmap[n]
OUTQ=[]
for q in Q:
    h=hull(q['pts']) if len(q['pts'])>=3 else []
    src=q['pts'] or q['apts']
    if not src: continue
    cxm=sum(p[0] for p in src)//len(src); cym=sum(p[1] for p in src)//len(src)
    b=which(cxm/1e6,cym/1e6)
    OUTQ.append({'h':h,'c':[cxm,cym],'hh':q['hh'],'len':round(q['len']),
                 'b':bi(BA[b]['nm'] if b is not None else 'Sem bairro'),'geo':1 if h else 0,
                 'num':q['num'],'setor':q['setor'][-5:]})
print("quadras:",len(OUTQ),"bairros:",len(bairros))

# ---------- simulate a campaign three weeks in ----------
PRIORITY={'Guamá':0.92,'Montese (Terra Firme)':0.88,'Jurunas':0.85,'Condor':0.80,'Cremação':0.72,
          'Pedreira':0.66,'Marambaia':0.60,'Cabanagem':0.58,'Tapanã':0.42,'Bengui':0.40,
          'Terra Firme':0.88,'Sacramenta':0.35,'Telégrafo':0.30,'Barreiro':0.28,'Una':0.22,
          'Marco':0.18,'São Brás':0.15,'Umarizal':0.10,'Batista Campos':0.08,'Nazaré':0.05}
FAV={'Guamá':0.63,'Montese (Terra Firme)':0.61,'Jurunas':0.66,'Condor':0.58,'Cremação':0.52,
     'Pedreira':0.55,'Marambaia':0.57,'Cabanagem':0.64,'Tapanã':0.60,'Bengui':0.59,
     'Marco':0.41,'Umarizal':0.34,'Batista Campos':0.31,'Nazaré':0.29,'São Brás':0.38}
tot=collections.Counter()
for q in OUTQ:
    nm=bairros[q['b']]
    p=PRIORITY.get(nm,0.05)*random.uniform(0.35,1.25)
    p=max(0,min(0.97,p))
    reached=int(q['hh']*p)
    fav=FAV.get(nm,0.45)*random.uniform(0.85,1.15)
    talked=int(reached*min(0.85,max(0.25,fav)))
    rest=reached-talked
    ausente=int(rest*0.62); recusou=int(rest*0.18); inexist=int(rest*0.12); naoloc=rest-ausente-recusou-inexist
    q['s']=[talked,ausente,recusou,inexist,max(0,naoloc)]
    for i,v in enumerate(q['s']): tot[i]+=v
    q.pop(None,None)
print("simulated:", dict(tot), "reached:",sum(tot.values()),"of",sum(q['hh'] for q in OUTQ))

# bairro border rings (thinned)
BB=[]
for b in BA:
    if b['nm'] not in bmap: continue
    rs=[[[round(p[0]*1e6),round(p[1]*1e6)] for p in pl[0][::3]] for pl in b['polys'] if len(pl[0])>8]
    if rs: BB.append({'b':bmap[b['nm']],'g':rs})
# daily series + canvassers
days=[]
base=sum(tot.values())
for d in range(21):
    days.append(int(base*( (d+1)/21 )**1.35 ))
crew=[]
NAMES=['Rai','Dhara','Iracema','Benedito','Maruan','Cleide','Josivaldo','Nayara','Ubiratã','Sâmia',
       'Reginaldo','Tainá','Elivelton','Marizete','Jocelino','Adriana']
for i,n in enumerate(NAMES):
    doors=int(random.uniform(280,1450)); conv=int(doors*random.uniform(0.42,0.68))
    crew.append({'n':n,'d':doors,'c':conv,'q':int(random.uniform(3,22))})
crew.sort(key=lambda c:-c['d'])
out={'b':bairros,'bb':BB,'q':OUTQ,'days':days,'crew':crew}
json.dump(out,open(d('belem-published.admin.json'),'w'),separators=(',',':'))
raw=open('admin.json','rb').read()
print("admin.json:",round(len(raw)/1024),"KB gzip:",round(len(gzip.compress(raw,9))/1024),"KB")
