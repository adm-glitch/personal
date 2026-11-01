"""Shared geometry helpers: GPKG blob reader, point-in-polygon, local metric projection.

Pure stdlib on purpose — the whole pipeline runs with nothing but CPython, so it works
on any machine that can run `verify.sh` without a GDAL/shapely install.
"""
import struct, math, sqlite3, os

def rings(blob):
    """Decode a GeoPackage geometry blob into [[outer, hole, ...], ...] rings of (x, y)."""
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
    """Point in ring, crossing-number."""
    ins=False;n=len(r);j=n-1
    for i in range(n):
        xi,yi=r[i];xj,yj=r[j]
        if ((yi>y)!=(yj>y)) and x<(xj-xi)*(y-yi)/(yj-yi+1e-18)+xi: ins=not ins
        j=i
    return ins

def shoelace(r):
    """Signed area of a ring, in the units of its coordinates."""
    a=0.0; n=len(r); j=n-1
    for i in range(n):
        a+=(r[j][0]-r[i][0])*(r[j][1]+r[i][1]); j=i
    return a/2.0

class Proj:
    """Equirectangular metres about a local origin. Good to <0.1% over one municipality."""
    def __init__(self, lon0, lat0):
        self.lon0, self.lat0 = lon0, lat0
        self.kx = 111320.0*math.cos(math.radians(lat0)); self.ky = 110574.0
    def fwd(self, lon, lat): return ((lon-self.lon0)*self.kx, (lat-self.lat0)*self.ky)
    def inv(self, x, y):     return (x/self.kx+self.lon0, y/self.ky+self.lat0)

def load_setores(gpkg, uf, mun):
    """Every censo-2022 setor of one municipality. This mesh tiles the municipality
    with no gaps — it is the only IBGE product that does at sub-bairro scale."""
    con=sqlite3.connect(gpkg)
    t=[r[0] for r in con.execute("select table_name from gpkg_contents")][0]
    out=[]
    for cd,sit,area,bai,geom in con.execute(
            f"select CD_SETOR, SITUACAO, AREA_KM2, NM_BAIRRO, geom from '{t}' where CD_MUN=?", (mun,)):
        if geom is None: continue
        polys=rings(geom)
        xs=[p[0] for pl in polys for r in pl for p in r]; ys=[p[1] for pl in polys for r in pl for p in r]
        if not xs: continue
        out.append({'cd':cd,'sit':sit,'area':area or 0.0,'bairro':bai,'polys':polys,
                    'bb':(min(xs),min(ys),max(xs),max(ys))})
    con.close()
    return out

def locate(x, y, feats):
    """Index of the first feature whose polygon contains (x, y), or None."""
    for i,f in enumerate(feats):
        x0,y0,x1,y1=f['bb']
        if not(x0<=x<=x1 and y0<=y<=y1): continue
        for pl in f['polys']:
            if pip(x,y,pl[0]) and not any(pip(x,y,h) for h in pl[1:]): return i
    return None

def indexed_locator(feats, cell=0.005):
    """locate() with a grid index over the bounding boxes. Belém is 2,085 setores against
    528,686 points — the linear scan is the difference between 6 s and several minutes."""
    import collections, math as _m
    G=collections.defaultdict(list)
    for i,f in enumerate(feats):
        x0,y0,x1,y1=f['bb']
        for gx in range(int(_m.floor(x0/cell)), int(_m.floor(x1/cell))+1):
            for gy in range(int(_m.floor(y0/cell)), int(_m.floor(y1/cell))+1): G[(gx,gy)].append(i)
    def at(x, y):
        for i in G.get((int(_m.floor(x/cell)), int(_m.floor(y/cell))), ()):
            x0,y0,x1,y1=feats[i]['bb']
            if not(x0<=x<=x1 and y0<=y<=y1): continue
            for pl in feats[i]['polys']:
                if pip(x,y,pl[0]) and not any(pip(x,y,h) for h in pl[1:]): return i
        return None
    return at

def simplify(r, g=10):
    """Quantise to ~1 m, then drop exactly-collinear vertices, returning 1e-6-degree ints.
    Both steps are a pure function of the coordinate, so an edge shared by two setores
    simplifies identically on both sides and the mesh stays gap-free. Per-ring
    simplification with a tolerance would open hairline slivers between neighbours."""
    p=[]
    for x,y in r:
        pt=(int(round(x*1e6/g))*g, int(round(y*1e6/g))*g)
        if not p or p[-1]!=pt: p.append(pt)
    if len(p)>1 and p[0]==p[-1]: p.pop()
    if len(p)<3: return p
    o=[b for i,b in enumerate(p)
       if (b[0]-p[i-1][0])*(p[(i+1)%len(p)][1]-p[i-1][1])
        - (b[1]-p[i-1][1])*(p[(i+1)%len(p)][0]-p[i-1][0]) != 0]
    return o if len(o)>=3 else p

def simplify_poly(pl):
    """[outer, hole...] simplified, outer wound CCW and holes CW so a single canvas path
    with nonzero winding cuts the holes out. 28 Belém setores enclose an enclave;
    painting over it would hide a whole setor."""
    o=[]
    for i,r in enumerate(pl):
        s=simplify(r)
        if len(s)<3: continue
        if (shoelace(s)>0) != (i==0): s.reverse()
        o.append(s)
    return o

def setor_shells(SET):
    """Group setor rows into one entry per CD_SETOR with simplified, hole-aware parts.
    A multipart setor arrives as one row per part, each repeating the whole setor's
    AREA_KM2 — group by code so the panel shows one setor, not five."""
    import collections
    ST=[]; owner=[None]*len(SET); grp={}
    for i,s in enumerate(SET):
        t=grp.get(s['cd'])
        if t is None:
            t=grp[s['cd']]={'g':[],'sit':1 if s['sit']=='Urbana' else 0,'cd':s['cd'][-6:],
                            'hh':0,'len':0,'s':[0,0,0,0,0],'b':0,'nq':0,'_b':collections.Counter()}
            ST.append(t)
        t['g'].extend(p for p in (simplify_poly(pl) for pl in s['polys']) if p)
        owner[i]=t
    return ST, owner
