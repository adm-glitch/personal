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

// "s3e14", "3x14", "t3 e14", or words of the English title.
function localMatches(q) {
  const f = fold(q);
  const se = f.match(/^[st]?\s*(\d)\s*[ex·.\s]\s*(\d{1,2})$/);
  if (se) {
    const e = byId.get(`S${se[1]}E${se[2].padStart(2, "0")}`);
    return e ? [e] : [];
  }
  if (f.length < 3) return [];
  return episodes.filter((e) => fold(e.title).includes(f)).slice(0, 3);
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
      h.textContent = e.title;
      const meta = document.createElement("div");
      meta.className = "meta";
      meta.textContent = e.airdate ? `estreou em ${e.airdate.slice(0, 4)}` : "";
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
  const sure = data.exists >= 0.5 && ranked[0]?.p >= 0.5;
  if (items[0] && sure) items[0] = { ...items[0], top: true };
  render(items, items.length ? (sure ? "" : "Não tenho certeza. Talvez um destes:") : "Não achei nada parecido.");
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
  timer = setTimeout(() => search(q), 350);
});

document.getElementById("examples").addEventListener("click", (ev) => {
  if (ev.target.tagName !== "BUTTON") return;
  input.value = ev.target.textContent;
  input.dispatchEvent(new Event("input"));
  input.focus();
});

input.focus();
