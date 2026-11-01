"""Derive block polygons by polygonising the kerb/street network.

Polygonising *any* noded line network partitions the plane completely — that is the
property we want for the coverage map, since every square metre lands in exactly one
cell. The open question this script answers is whether the resulting cells are
*meaningful*: a cell should be one quadra, not a blob that swallowed six of them
because the lines between them were never drawn.

    python3 pipeline/polygonize.py 1508209 [--osm] [--no-ibge] [--out data/vigia.blocks.json]

Reports the numbers; writes the cells only when asked. Pure stdlib.
"""
import sys, os, json, zipfile, math, collections, statistics
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from geo import Proj, shoelace, load_setores, pip

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
UFC  = {'11':'RO','12':'AC','13':'AM','14':'RR','15':'PA','16':'AP','17':'TO','21':'MA',
        '22':'PI','23':'CE','24':'RN','25':'PB','26':'PE','27':'AL','28':'SE','29':'BA',
        '31':'MG','32':'ES','33':'RJ','35':'SP','41':'PR','42':'SC','43':'RS','50':'MS',
        '51':'MT','52':'GO','53':'DF'}

MUN  = sys.argv[1]
USE_OSM  = '--osm' in sys.argv
USE_IBGE = '--no-ibge' not in sys.argv
OUT  = None
if '--out' in sys.argv: OUT = sys.argv[sys.argv.index('--out')+1]
UF = UFC[MUN[:2]]
def d(*p): return os.path.join(DATA, *p)

SNAP = 50      # cm — node-merge tolerance. Opposite kerbs of a 3 m beco stay distinct.
if '--snap' in sys.argv: SNAP = int(sys.argv[sys.argv.index('--snap')+1])
CELL = 2500    # cm — spatial index cell (25 m)

# ---------------------------------------------------------------- 1. gather lines
lines = []                      # list of [(lon,lat), ...]
zf = zipfile.ZipFile(d(UF+'_faces.zip'))
rawf = json.loads(zf.open(f'{UF}/{MUN}_faces_de_logradouros_2022.json').read())['features']
if USE_IBGE:
    for f in rawf:
        g = f['geometry']['coordinates']
        if len(g) >= 2: lines.append([(c[0], c[1]) for c in g])
n_ibge = len(lines)
if USE_OSM:
    rd = json.load(open(d(f'roads_{MUN}.json')))
    for e in rd['elements']:
        g = e.get('geometry')
        if g and len(g) >= 2: lines.append([(p['lon'], p['lat']) for p in g])
print(f"{MUN}: {n_ibge} IBGE kerb lines + {len(lines)-n_ibge} OSM ways")

xs = [p[0] for L in lines for p in L]; ys = [p[1] for L in lines for p in L]
P = Proj(sum(xs)/len(xs), sum(ys)/len(ys))
def to_cm(lon, lat):
    x, y = P.fwd(lon, lat); return (round(x*100), round(y*100))

# ---------------------------------------------------------------- 2. segment soup
segs = []
for L in lines:
    pts = [to_cm(*c) for c in L]
    for i in range(len(pts)-1):
        if pts[i] != pts[i+1]: segs.append((pts[i], pts[i+1]))
print(f"  {len(segs)} segments")

# ---------------------------------------------------------------- 3. split at crossings
grid = collections.defaultdict(list)
for i, (a, b) in enumerate(segs):
    x0, x1 = sorted((a[0], b[0])); y0, y1 = sorted((a[1], b[1]))
    for cx in range(x0//CELL, x1//CELL+1):
        for cy in range(y0//CELL, y1//CELL+1): grid[(cx, cy)].append(i)

cuts = collections.defaultdict(set)
checked = set()
for ids in grid.values():
    for ii in range(len(ids)):
        for jj in range(ii+1, len(ids)):
            i, j = ids[ii], ids[jj]
            k = (i, j) if i < j else (j, i)
            if k in checked: continue
            checked.add(k)
            (ax, ay), (bx, by) = segs[i]; (cx, cy), (dx, dy) = segs[j]
            rx, ry = bx-ax, by-ay; sx, sy = dx-cx, dy-cy
            den = rx*sy - ry*sx
            if den == 0: continue                      # parallel or collinear
            qpx, qpy = cx-ax, cy-ay
            t = (qpx*sy - qpy*sx)/den
            u = (qpx*ry - qpy*rx)/den
            if not (0.0 < t < 1.0 and 0.0 < u < 1.0): continue   # endpoint touches are already nodes
            cuts[i].add(t); cuts[j].add(u)
print(f"  {sum(len(v) for v in cuts.values())} crossing splits on {len(cuts)} segments")

# ---------------------------------------------------------------- 4. node and build graph
nodes = collections.defaultdict(list); NP = []
def nid(p):
    """Merge to any existing node within SNAP. Buckets alone would miss pairs that
    straddle a bucket edge, which is most of them — so search the 3x3 neighbourhood."""
    bx, by = p[0]//SNAP, p[1]//SNAP
    best = None; bd = SNAP*SNAP
    for gx in (bx-1, bx, bx+1):
        for gy in (by-1, by, by+1):
            for i in nodes.get((gx, gy), ()):
                dx = NP[i][0]-p[0]; dy = NP[i][1]-p[1]; dd = dx*dx+dy*dy
                if dd <= bd: best, bd = i, dd
    if best is not None: return best
    i = len(NP); NP.append(p); nodes[(bx, by)].append(i)
    return i

edges = set()
for i, (a, b) in enumerate(segs):
    ts = sorted(cuts.get(i, ()))
    pts = [a] + [(round(a[0]+(b[0]-a[0])*t), round(a[1]+(b[1]-a[1])*t)) for t in ts] + [b]
    ids = [nid(p) for p in pts]
    for u, v in zip(ids, ids[1:]):
        if u != v: edges.add((u, v) if u < v else (v, u))
print(f"  planar graph: {len(NP)} nodes, {len(edges)} edges")

adj = collections.defaultdict(list)
for u, v in edges:
    adj[u].append(v); adj[v].append(u)
ang = {}
for u, ns in adj.items():
    ns.sort(key=lambda v: math.atan2(NP[v][1]-NP[u][1], NP[v][0]-NP[u][0]))
    ang[u] = {v: i for i, v in enumerate(ns)}

# ---------------------------------------------------------------- 5. trace faces
# From half-edge u->v, the next half-edge is v->w where w is the neighbour of v
# immediately clockwise from u. This traces interior faces counter-clockwise
# (positive shoelace); each connected component's outer face comes out negative.
seen = set(); cells = []; outer = 0
for u0, v0 in list(edges) + [(v, u) for u, v in edges]:
    if (u0, v0) in seen: continue
    ring = []; u, v = u0, v0
    while (u, v) not in seen:
        seen.add((u, v)); ring.append(v)
        ns = adj[v]; w = ns[(ang[v][u] - 1) % len(ns)]
        u, v = v, w
    r = [NP[i] for i in ring]
    a = shoelace(r)/1e4                     # cm^2 -> m^2
    if a > 0: cells.append({'r': ring, 'a': a})
    else: outer += 1
print(f"  {len(cells)} interior cells, {outer} outer/component rings")

# ---------------------------------------------------------------- 6. households and setores
z = zipfile.ZipFile(d(f'cnefe_{MUN}.json.zip'))
res = [f for f in json.loads(z.open(z.namelist()[0]).read())['features']
       if f['properties']['COD_ESPECIE'] == '1']
H = []
for f in res:
    p = f['properties']
    x, y = to_cm(*f['geometry']['coordinates'][:2])
    H.append((x, y, (p['COD_SETOR'], p['NUM_QUADRA'])))

cgrid = collections.defaultdict(list)
for ci, c in enumerate(cells):
    r = [NP[i] for i in c['r']]
    x0 = min(p[0] for p in r); x1 = max(p[0] for p in r)
    y0 = min(p[1] for p in r); y1 = max(p[1] for p in r)
    c['bb'] = (x0, y0, x1, y1); c['ring'] = r; c['hh'] = collections.Counter()
    for gx in range(x0//CELL, x1//CELL+1):
        for gy in range(y0//CELL, y1//CELL+1): cgrid[(gx, gy)].append(ci)

lost = 0
for x, y, q in H:
    hit = None
    for ci in cgrid.get((x//CELL, y//CELL), ()):
        x0, y0, x1, y1 = cells[ci]['bb']
        if x0 <= x <= x1 and y0 <= y <= y1 and pip(x, y, cells[ci]['ring']):
            # smallest containing cell wins — an enclosed component sits inside its parent
            if hit is None or cells[ci]['a'] < cells[hit]['a']: hit = ci
    if hit is None: lost += 1
    else: cells[hit]['hh'][q] += 1

# ---------------------------------------------------------------- 7. report
occ = [c for c in cells if c['hh']]
areas = sorted(c['a'] for c in occ)
hhc = sorted(sum(c['hh'].values()) for c in occ)
nq = [len(c['hh']) for c in occ]
qspan = collections.defaultdict(set)
for ci, c in enumerate(occ):
    for q in c['hh']: qspan[q].add(ci)
spans = sorted(len(v) for v in qspan.values())

def pct(v, p): return v[min(len(v)-1, len(v)*p//100)]
print()
print(f"  cells with households      {len(occ)} of {len(cells)}")
print(f"  households placed          {len(H)-lost} of {len(H)}  ({(len(H)-lost)/len(H)*100:.1f}%)")
print(f"  cell area m2               median {statistics.median(areas):,.0f}  p10 {pct(areas,10):,.0f}  p90 {pct(areas,90):,.0f}  max {max(areas):,.0f}")
print(f"  households per cell        median {statistics.median(hhc):.0f}  p90 {pct(hhc,90)}  max {max(hhc)}")
print(f"  IBGE quadras per cell      median {statistics.median(nq):.0f}  mean {sum(nq)/len(nq):.2f}  "
      f"| 1 quadra: {sum(1 for n in nq if n==1)/len(nq)*100:.0f}%  5+: {sum(1 for n in nq if n>=5)/len(nq)*100:.0f}%")
print(f"  cells per IBGE quadra      median {statistics.median(spans):.0f}  mean {sum(spans)/len(spans):.2f}  "
      f"| 1 cell: {sum(1 for n in spans if n==1)/len(spans)*100:.0f}%")
pure = sum(max(c['hh'].values()) for c in occ)
print(f"  purity (hh in modal quadra of its cell) {pure/(len(H)-lost)*100:.1f}%")

sfile = d(UF+'_setores.gpkg')
if os.path.exists(sfile):
    S = load_setores(sfile, UF, MUN)
    urb = [s for s in S if s['sit'] == 'Urbana']
    ua = sum(s['area'] for s in urb)
    print(f"  setores {len(S)} ({len(urb)} urbanos, {ua:.2f} km2) | cells cover "
          f"{sum(c['a'] for c in cells)/1e6:.2f} km2 total, occupied cells {sum(c['a'] for c in occ)/1e6:.2f} km2")

if OUT:
    json.dump({'proj': [P.lon0, P.lat0],
               'cells': [{'g': [list(P.inv(p[0]/100, p[1]/100)) for p in c['ring']],
                          'a': round(c['a']), 'hh': sum(c['hh'].values())} for c in occ]},
              open(OUT, 'w'), separators=(',', ':'))
    print(f"  wrote {OUT} ({os.path.getsize(OUT)/1024:.0f} KB)")
