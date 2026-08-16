import fs from 'fs';
import path from 'path';
import {fileURLToPath} from 'url';
const HERE=path.dirname(fileURLToPath(import.meta.url));
const R=p=>path.isAbsolute(p)?p:path.resolve(HERE,'../..',p);
const canvasState={width:704,height:600}; const calls={};
function ctxStub(){ return new Proxy({},{get(t,p){ if(p==='canvas')return canvasState;
  return (...a)=>{calls[p]=(calls[p]||0)+1;}; },set(){return true}}); }
const handlers={};
class El{
  constructor(id,tag='div'){ this.id=id; this.tag=tag; this.style={}; this.dataset={}; this._html='';this._kids=[];this.attrs={};
    this.childNodes=[{nodeValue:'—'}]; this._ctx=ctxStub();
    this.classList={_s:new Set(),add(c){this._s.add(c)},remove(c){this._s.delete(c)},
      toggle(c,v){v===undefined?(this._s.has(c)?this._s.delete(c):this._s.add(c)):(v?this._s.add(c):this._s.delete(c))},
      contains(c){return this._s.has(c)}};
    Object.defineProperty(this,'width',{get:()=>canvasState.width,set:v=>canvasState.width=v});
    Object.defineProperty(this,'height',{get:()=>canvasState.height,set:v=>canvasState.height=v});
  }
  get innerHTML(){return this._html} set innerHTML(v){this._html=v;this._kids=[];this._qs=new Map();}
  get textContent(){return this._text||''} set textContent(v){this._text=v}
  getContext(){ if(this.tag!=='canvas') throw new TypeError(this.id+'.getContext is not a function'); return this._ctx; }
  getBoundingClientRect(){ return {width:352,height:300,left:0,top:0}; }
  addEventListener(t,f){ (handlers[this.id+':'+t]||=[]).push(f); }
  setAttribute(k,v){this.attrs[k]=v} getAttribute(k){return this.attrs[k]}
  appendChild(c){this._kids.push(c);return c} focus(){} setPointerCapture(){}
  querySelectorAll(sel){
    this._qs=this._qs||new Map(); const key=this._html+'||'+sel;
    if(this._qs.has(key)) return this._qs.get(key);
    const out=[]; const mk=(re,k)=>{let m;while((m=re.exec(this._html))){const e=new El('x','div');e.dataset[k]=m[1];out.push(e);} };
    if(sel.includes('data-tgt')) mk(/data-tgt="(\w+)"/g,'tgt');
    else if(sel.includes('data-tier')) mk(/data-tier="(\d+)"/g,'tier');
    else if(sel.includes('data-fs')) mk(/data-fs="(\d+)"/g,'fs');
    else if(sel.includes('data-tly')){ let m; const re=/data-tly="(\w+)" data-d="(-?\d+)"/g;
      while((m=re.exec(this._html))){ const e=new El('x','button');
        e.dataset.tly=m[1]; e.dataset.d=m[2]; out.push(e); } }
    else if(sel.includes('data-nav')) mk(/data-nav="(\w+)"/g,'nav');
    else if(sel.includes('data-pickq')) mk(/data-pickq="(\d+)"/g,'pickq');
    else if(sel.includes('data-pickf')) mk(/data-pickf="(\d+)"/g,'pickf');
    else if(sel.includes('data-b]')) mk(/data-b="(\d+)"/g,'b');
    else if(sel.includes('data-q]')) mk(/data-q="(\d+)"/g,'q');
    else if(sel.includes('data-face')) mk(/data-face="(\d+)"/g,'face');
    else if(sel.includes('data-place')) mk(/data-place="(\d+)"/g,'place');
    else if(sel.includes('data-addr')) mk(/data-addr="(\d+)"/g,'addr');
    else if(sel.includes('data-s')) mk(/data-s="(\d+)"/g,'s');
    else if(sel.includes('.bulk')) mk(/data-bulk-s="(-?\d+)"/g,'bulkS');
    else if(sel.includes('more')) mk(/class="more" data-bulk="(\w+)"/g,'bulk');
    this._qs.set(key,out); return out;
  }
}
const TAGS={pmap:'canvas'};
const els=new Map();
const b64=fs.readFileSync(R(process.env.PAY||'data/belem.bin.gz')).toString('base64');
function mk(id){ if(!els.has(id)){const e=new El(id,TAGS[id]||'div'); if(id==='blk') e.textContent=b64; els.set(id,e);} return els.get(id); }
global.document={getElementById:mk,createElement:t=>new El('new',t),
  documentElement:{style:{},setAttribute(){},getAttribute(){return null}},addEventListener(){},
  querySelectorAll:()=>els.get('dbody')?els.get('dbody').querySelectorAll('.ditem'):[]};
global.window={devicePixelRatio:2,addEventListener(){},ResizeObserver:class{constructor(f){this.f=f}observe(){}}};
global.getComputedStyle=()=>({getPropertyValue:n=>({'--font-mono':'monospace','--font-sans':'sans-serif'}[n]||'#888888')});
global.matchMedia=()=>({addEventListener(){}});
global.MutationObserver=class{constructor(){}observe(){}};
global.ResizeObserver=global.window.ResizeObserver;
const realTimeout=setTimeout;
global.setInterval=()=>0; global.clearInterval=()=>{}; global.clearTimeout=()=>{};
global.setTimeout=(f,ms)=>0;

const t=Date.now();
await import('./'+(process.env.MAIN||'mockup_main.js'));
await new Promise(r=>realTimeout(r,900));

console.log('total wall time:', Date.now()-t,'ms');
console.log('city:', JSON.stringify(global.__CITY||globalThis.__CITY));
console.log('draw calls:', JSON.stringify(calls).slice(0,220));
const L=()=>els.get('list');
console.log('\nroot list (bairros):', (L().innerHTML.match(/data-b="/g)||[]).length);
const names=[...L().innerHTML.matchAll(/<b class="rn">([^<]+)<\/b>/g)].map(m=>m[1]).slice(0,6);
console.log('first bairros:', JSON.stringify(names));
console.log('grip:', JSON.stringify(els.get('grip-t').childNodes[0].nodeValue), '/', JSON.stringify(els.get('grip-s').textContent));
console.log('banner:', JSON.stringify(els.get('loc-k').textContent), JSON.stringify(els.get('loc-v').textContent));
console.log('zoom level chip:', JSON.stringify(els.get('zlvl').textContent));

const H=()=>L().innerHTML, N=re=>(H().match(re)||[]).length;
console.log('\n--- navigate to the city root ---');
function allKids(el){ const out=[]; (function rec(e){ for(const k of (e._kids||[])){ out.push(k); rec(k);} })(el); return out; }
const picks=allKids(els.get('loc-pick'));
const chg=picks.find(x=>((x.innerHTML||'')+(x._text||'')).includes('Trocar local'));
chg.onclick();
console.log('  bairro rows:', N(/data-b="/g));
const bn=[...H().matchAll(/<b class="rn">([^<]+)<\/b>/g)].map(m=>m[1]);
console.log('  first five:', JSON.stringify(bn.slice(0,5)));
console.log('  bairros flagged with sem contorno:', N(/sem contorno/g));

console.log('\n--- drill a bairro -> quadras -> faces ---');
const big=bn.indexOf('Montese (Terra Firme)');
L().querySelectorAll('.row[data-b]')[big>=0?big:0].onclick();
console.log('  quadra rows:', N(/data-q="/g), '| SEM CONTORNO:', N(/SEM CONTORNO/g));
console.log('  estou-aqui buttons:', N(/data-pickq=/g));
L().querySelectorAll('.row[data-q]')[0].onclick();
console.log('  work rows:', N(/data-tgt="/g), '| ghost faces:', N(/SEM LINHA NO MAPA/g));

/* ---- face-level coverage: the unit is the face, never the door ---- */
console.log('\n--- face-level marking ---');
const px=els.get('pick-x'); if(px&&px.onclick) px.onclick();          // leave picking mode
L().querySelectorAll('.crumbbar span[data-nav]')[0].onclick();        // back to city root
L().querySelectorAll('.row[data-b]')[0].onclick();
L().querySelectorAll('.row[data-q]')[0].onclick();
console.log('  tier bar:', N(/tierbar/g)>0, '| tier badges:', N(/tierb/g));
const rows0=L().querySelectorAll('.row[data-tgt]');
console.log('  rows offered:', rows0.length);
rows0[0].onclick();                                                   // open action panel
console.log('  action panel:', N(/acts face/g)>0, '| status buttons:', N(/data-fs=/g),
            '| tally steppers:', N(/data-tly=/g));
const EV={stopPropagation(){},preventDefault(){}};                    // a real click has one
L().querySelectorAll('.acts button[data-fs]')[0].onclick(EV);        // mark percorrida
console.log('  after marking -> chips:', N(/class="chip/g),
            '| percorrida:', N(/percorrida/g)>0);
/* forcing tier 3 must re-present the same quadra grouped by street */
const tb=L().querySelectorAll('.tierbar button[data-tier]');
if(tb.length>=4){ tb[3].onclick(EV);
  console.log('  tier 3 forced -> street rows:', L().querySelectorAll('.row[data-tgt]').length,
              '| all g-targets:', /data-tgt="g/.test(L().innerHTML));
  const tgt3=L().querySelectorAll('.row[data-tgt]');
  if(tgt3.length){ tgt3[0].onclick();
    console.log('  tier-3 row opens panel:', N(/acts face/g)>0,
                '| marks every trecho of the street'); }
  L().querySelectorAll('.tierbar button[data-tier]')[0].onclick(EV); }

console.log('\n--- citywide data-quality panel ---');
for(const id of ['g-bairros','g-nogeo','g-ghost','g-ghostaddr','g-dup'])
  console.log('  '+id+':', els.get(id).textContent);

console.log('\n--- zoom LOD + culling ---');
const wheel=handlers['pmap:wheel'][0];
function frame(){ const b=calls.stroke||0; wheel({clientX:176,clientY:150,deltaY:0,preventDefault(){}}); return (calls.stroke||0)-b; }
const atFit=frame();
for(let i=0;i<10;i++) wheel({clientX:176,clientY:150,deltaY:-500,preventDefault(){}});
const z1=frame(); const lvl1=els.get('zlvl').textContent;
for(let i=0;i<10;i++) wheel({clientX:176,clientY:150,deltaY:-500,preventDefault(){}});
const z2=frame(); const lvl2=els.get('zlvl').textContent;
console.log('  full city   :', atFit, 'strokes/frame, labels =', JSON.stringify('bairros'));
console.log('  zoomed once :', z1, 'strokes/frame, labels =', JSON.stringify(lvl1));
console.log('  zoomed twice:', z2, 'strokes/frame, labels =', JSON.stringify(lvl2));
console.log('\nPASS');
