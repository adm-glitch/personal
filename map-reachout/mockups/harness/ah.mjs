import fs from 'fs';
import path from 'path';
import {fileURLToPath} from 'url';
const HERE=path.dirname(fileURLToPath(import.meta.url));
const R=p=>path.isAbsolute(p)?p:path.resolve(HERE,'../..',p);
const cs={width:1200,height:900}, calls={};
const ctxStub=()=>new Proxy({},{get(t,p){ if(p==='canvas')return cs;
  return (...a)=>{calls[p]=(calls[p]||0)+1;}; },set(){return true}});
const handlers={};
class El{
  constructor(id,tag='div'){this.id=id;this.tag=tag;this.style={};this.dataset={};this._html='';this.attrs={};
    this.childNodes=[{nodeValue:'—'}];this._ctx=ctxStub();
    this.classList={_s:new Set(),add(c){this._s.add(c)},remove(c){this._s.delete(c)},toggle(c,v){v?this._s.add(c):this._s.delete(c)},contains(c){return this._s.has(c)}};
    Object.defineProperty(this,'width',{get:()=>cs.width,set:v=>cs.width=v});
    Object.defineProperty(this,'height',{get:()=>cs.height,set:v=>cs.height=v});}
  get innerHTML(){return this._html} set innerHTML(v){this._html=v}
  get textContent(){return this._text||''} set textContent(v){this._text=v}
  getContext(){ if(this.tag!=='canvas') throw new TypeError(this.id+'.getContext is not a function'); return this._ctx; }
  getBoundingClientRect(){ return {width:820,height:520,left:0,top:0}; }
  addEventListener(t,f){(handlers[this.id+':'+t]||=[]).push(f);}
  setAttribute(k,v){this.attrs[k]=v} getAttribute(k){return this.attrs[k]}
  querySelectorAll(){return []} focus(){} setPointerCapture(){}
}
const TAGS={map:'canvas',trend:'canvas'};
const els=new Map();
const data=fs.readFileSync(R(process.env.ADATA||'data/belem.admin.json'),'utf8');
const mk=id=>{ if(!els.has(id)){const e=new El(id,TAGS[id]||'div'); if(id==='data') e.textContent=data; els.set(id,e);} return els.get(id); };
global.document={getElementById:mk,createElement:t=>new El('n',t),
  documentElement:{style:{},setAttribute(){},getAttribute(){return null}},addEventListener(){},
  querySelectorAll:()=>[]};
global.window={devicePixelRatio:2,addEventListener(){},ResizeObserver:class{constructor(f){this.f=f}observe(){}}};
global.getComputedStyle=()=>({getPropertyValue:n=>({'--font-mono':'monospace','--font-sans':'sans-serif'}[n]||'#888888')});
global.matchMedia=()=>({addEventListener(){}});
global.MutationObserver=class{constructor(){}observe(){}};
global.ResizeObserver=global.window.ResizeObserver;

const t=Date.now();
try{ await import('./admin_main.js'); }catch(e){ console.log('THREW:',e.message); console.log(e.stack.split('\n').slice(0,4).join('\n')); process.exit(1);}
console.log('boot ok in',Date.now()-t,'ms');
console.log('draw calls:',JSON.stringify(calls).slice(0,190));
const txt=id=>els.get(id).innerHTML||els.get(id).textContent;
console.log('\nKPIs:', (txt('kpis').match(/class="v">([^<]+)/g)||[]).map(s=>s.split('>')[1]).join(' | '));
console.log('map header:', els.get('maph-n').textContent);
console.log('legend has ramp:', txt('legend').includes('ramp'));
console.log('rank rows:', (txt('rank').match(/class="rrow/g)||[]).length, '| count:', els.get('rank-n').textContent);
console.log('stack pcts:', (txt('stleg').match(/<b>([^<]+)<\/b>/g)||[]).join(' '));
console.log('priority rows:', (txt('prio').match(/<tr>/g)||[]).length);
console.log('audit rows:', (txt('audit').match(/<tr/g)||[]).length);
console.log('crew rows:', (txt('crew').match(/<tr>/g)||[]).length);

console.log('\n--- metric switch ---');
els.get('m-dom').onclick();
console.log('  dominant legend:', txt('legend').includes('Situação dominante'), '| classes:', (txt('legend').match(/class="cat"/g)||[]).length);
els.get('m-pend').onclick();
console.log('  header:', els.get('maph-n').textContent);
els.get('m-falei').onclick();

console.log('\n--- status toggles change the numbers ---');
const before=(txt('kpis').match(/class="v">([^<]+)/)||[])[1];
els.get('t1').onclick(); els.get('t2').onclick(); els.get('t3').onclick(); els.get('t4').onclick();
const after=(txt('kpis').match(/class="v">([^<]+)/)||[])[1];
console.log('  alcançados all statuses:', before, '-> only "falei":', after);

console.log('\n--- level toggle ---');
els.get('lvl').onclick();
console.log('  after 1 click:', els.get('lvl').textContent, '|', els.get('maph-n').textContent);
els.get('lvl').onclick();
console.log('  after 2 clicks:', els.get('lvl').textContent, '|', els.get('maph-n').textContent);
console.log('  rank rows now:', (txt('rank').match(/class="rrow/g)||[]).length);

const D=JSON.parse(data);
if(D.st && D.st.length){
  console.log('\n--- setor layer paints the whole territory ---');
  const nst=D.st.length, parts=D.st.reduce((s,t)=>s+t.g.length,0);
  // button is on 'setor'; walk round to 'bairro', clear, then step into 'setor' so the
  // fill count belongs to exactly one setor-level draw
  els.get('lvl').onclick();                 // -> quadra
  els.get('lvl').onclick();                 // -> auto
  els.get('lvl').onclick();                 // -> bairro
  for(const k in calls) delete calls[k];
  els.get('lvl').onclick();                 // -> setor
  const fills=calls.fill||0;
  // a couple of parts sit outside the fitted viewport and are culled — allow for that
  console.log('  setores:', nst, '| parts:', parts, '| filled at setor level:', fills,
              '('+(parts-fills)+' culled off-screen)');
  if(fills < parts*0.9) { console.log('FAIL: setor level filled only', fills, 'of', parts, 'parts'); process.exit(1); }
  const rank=txt('rank');
  if(!/Setor …/.test(rank)) { console.log('FAIL: setor level rank list has no setor rows'); process.exit(1); }
  els.get('lvl').onclick();                 // -> quadra, must not throw with ST present
  console.log('  quadra level over setor fill:', els.get('maph-n').textContent);
  els.get('lvl').onclick();                 // back to auto
}
console.log('\nPASS');
