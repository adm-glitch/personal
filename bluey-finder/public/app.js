// Type → instant title matches from the local list → Jev ranking ~0.5 s later.
const input = document.getElementById("q");
const list = document.getElementById("results");
const status = document.getElementById("status");
const episodes = await (await fetch("episodes.json")).json();
const byId = new Map(episodes.map((e) => [e.id, e]));
const cache = new Map();
let timer = 0;
let inflight = null;

const fold = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim();

// What instant matching looks at: titles (pt + en), aliases and "coisas" (things a child names: peixe, balão…).
const terms = new Map(episodes.map((e) => [e.id, {
  titles: [e.pt, e.title].filter(Boolean).map(fold),
  phrases: [...(e.aliases ?? []), ...(e.coisas ?? [])].map(fold),
}]));

// Leading filler a child or parent types: "o episódio do peixe" → "peixe".
const strip = (f) => f.replace(/^(o|a)?\s*(episodio|desenho|aquele|aquela|esse|essa)?\s*(d[oa]s?|que|com|em que)?\s+/, "").trim() || f;

// "s3e14", "3x14", "t3 e14", or a title / alias / thing. Exact thing first ("peixe" before "peixe com fritas").
function localMatches(q) {
  const f = fold(q);
  const se = f.match(/^[st]?\s*(\d)\s*[ex·.\s]\s*(\d{1,2})$/);
  if (se) {
    const e = byId.get(`S${se[1]}E${se[2].padStart(2, "0")}`);
    return e ? [e] : [];
  }
  const w = strip(f);
  if (w.length < 3) return [];
  const score = (t) => {
    if (t.titles.some((x) => x === w)) return 4;
    if (t.phrases.some((x) => x === w)) return 3;
    if (t.titles.some((x) => x.includes(w))) return 2;
    if (t.phrases.some((x) => x.startsWith(w) || x.includes(` ${w}`))) return 1;
    return 0;
  };
  return episodes
    .map((e) => ({ e, s: score(terms.get(e.id)) }))
    .filter((x) => x.s > 0)
    .sort((a, b) => b.s - a.s)
    .slice(0, 6)
    .map((x) => x.e);
}

function render(items, note = "") {
  status.textContent = note;
  list.replaceChildren(
    ...items.map((e, i) => {
      const li = document.createElement("li");
      if (i === 0 && items.length && e.top) li.className = "top";
      const img = document.createElement("img");
      img.src = (e.top ? e.still : e.image) ?? e.image ?? "";
      img.alt = "";
      img.loading = "lazy";
      const body = document.createElement("div");
      const se = document.createElement("span");
      se.className = "se";
      se.textContent = `Temporada ${e.season} · Episódio ${e.number}`;
      const h = document.createElement("h2");
      h.textContent = e.pt ?? e.title;
      const meta = document.createElement("div");
      meta.className = "meta";
      meta.textContent = [e.pt && e.pt !== e.title ? e.title : "", e.airdate?.slice(0, 4)].filter(Boolean).join(" · ");
      body.append(se, h, meta);
      li.append(img, body);
      return li;
    }),
  );
}

function show(q, data) {
  const local = localMatches(q);
  const ranked = (data?.results ?? []).filter((r, i) => i === 0 || r.p >= 0.04).slice(0, 6);
  const seen = new Set();
  const items = [];
  for (const r of ranked) {
    const e = byId.get(r.id);
    if (e && !seen.has(e.id)) { seen.add(e.id); items.push({ ...e, p: r.p }); }
  }
  for (const e of local) if (!seen.has(e.id)) { seen.add(e.id); items.push(e); }
  if (!data) return render(local, local.length ? "" : "procurando…");
  // One word that several episodes share ("peixe"): no single winner, let the child pick by the picture,
  // episodes that literally have the thing first, then Jev's guesses.
  const word = strip(fold(q));
  const shared = word.split(" ").length <= 2 && local.length >= 2;
  if (shared) {
    const at = (e) => { const i = local.findIndex((x) => x.id === e.id); return i < 0 ? local.length : i; };
    items.sort((a, b) => at(a) - at(b)); // stable: Jev's order is kept among the rest
  }
  items.splice(8);
  const sure = !shared && data.exists >= 0.5 && ranked[0]?.p >= 0.5;
  if (items[0] && sure) items[0] = { ...items[0], top: true };
  const note = shared ? `Vários episódios têm “${word}”. Qual destes?` : sure ? "" : "Não tenho certeza. Talvez um destes:";
  render(items, items.length ? note : "Não achei nada parecido.");
}

async function search(q) {
  const key = fold(q);
  if (cache.has(key)) return show(q, cache.get(key));
  inflight?.abort();
  inflight = new AbortController();
  document.body.classList.add("loading");
  try {
    const res = await fetch(`/api/search?q=${encodeURIComponent(q)}`, { signal: inflight.signal });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error ?? res.status);
    cache.set(key, data);
    if (fold(input.value) === key) show(q, data);
  } catch (err) {
    if (err.name === "AbortError") return;
    render(localMatches(q), res429(err) ? "Muitas buscas seguidas, espere um pouquinho." : "A busca está fora do ar agora.");
  } finally {
    document.body.classList.remove("loading");
  }
}
const res429 = (err) => String(err.message).includes("slow down");

input.addEventListener("input", () => {
  const q = input.value.trim();
  document.body.classList.toggle("searching", q.length > 0);
  clearTimeout(timer);
  if (q.length < 3) { inflight?.abort(); return render(localMatches(q)); }
  show(q, cache.get(fold(q)));
  timer = setTimeout(() => search(q), 250);
});

document.getElementById("examples").addEventListener("click", (ev) => {
  if (ev.target.tagName !== "BUTTON") return;
  input.value = ev.target.textContent;
  input.dispatchEvent(new Event("input"));
  input.focus();
});

input.focus();
