// Builds data/episodes.json: every Bluey episode with season, number, title, still and a short plot.
// Episodes + stills: TVMaze API (CC BY-SA). Plots: Blueypedia via the MediaWiki API (CC BY-SA).
// Plots are only sent to Jev as search context; the page shows title, number and still.
// Run: node scripts/build-episodes.mjs
import { writeFile, mkdir } from "node:fs/promises";

const UA = "bluey-finder/0.1 (family fan project; github.com/adm-glitch/bluey-finder)";
const WIKI = "https://blueypedia.fandom.com/api.php";
const SHOW_ID = 41821; // TVMaze: Bluey (2018)
const PLOT_CHARS = 700;

async function getJson(url) {
  const res = await fetch(url, { headers: { "User-Agent": UA } });
  if (!res.ok) throw new Error(`${res.status} ${url}`);
  return res.json();
}

const wiki = (params) => getJson(`${WIKI}?${new URLSearchParams({ format: "json", ...params })}`);

// Strip the wiki markup we meet in synopses: links, bold/italics, templates, refs, comments.
function plain(text) {
  return text
    .replace(/<!--[\s\S]*?-->/g, "")
    .replace(/<ref[\s\S]*?(<\/ref>|\/>)/g, "")
    .replace(/<[^>]+>/g, "")
    .replace(/\{\{[^{}]*\}\}/g, "")
    .replace(/\[\[(?:[^|\]]*\|)?([^\]]+)\]\]/g, "$1")
    .replace(/'{2,}/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

// Reads one named parameter of the {{Synopsis ...}} template.
function synopsisParam(wikitext, name) {
  const start = wikitext.indexOf("{{Synopsis");
  if (start < 0) return "";
  const body = wikitext.slice(start);
  const m = body.match(new RegExp(`\\|\\s*${name}\\s*=([\\s\\S]*?)(?=\\n\\s*\\|\\s*\\w+\\s*=|\\n\\}\\})`));
  return m ? plain(m[1]) : "";
}

// Older pages use plain sections (==Synopsis==, ==Episode Recap==) instead of the template.
function section(wikitext, ...names) {
  for (const name of names) {
    const m = wikitext.match(new RegExp(`^==\\s*${name}\\s*==\\s*$([\\s\\S]*?)(?=^==[^=])`, "mi"));
    if (m) {
      const text = plain(m[1].replace(/'''Warning Spoilers!\s*'''/i, ""));
      if (text) return text;
    }
  }
  return "";
}

function clip(text, max) {
  if (text.length <= max) return text;
  const cut = text.slice(0, max);
  return cut.slice(0, cut.lastIndexOf(" ")) + "…";
}

async function categoryTitles() {
  const titles = new Map(); // lowercase -> real page title
  let cont = {};
  do {
    const r = await wiki({ action: "query", list: "categorymembers", cmtitle: "Category:Episodes", cmlimit: "500", cmnamespace: "0", ...cont });
    for (const p of r.query.categorymembers) titles.set(p.title.toLowerCase(), p.title);
    cont = r.continue ?? null;
  } while (cont);
  return titles;
}

async function wikitexts(titles) {
  const out = new Map();
  for (let i = 0; i < titles.length; i += 50) {
    const batch = titles.slice(i, i + 50);
    const r = await wiki({ action: "query", prop: "revisions", rvprop: "content", rvslots: "main", titles: batch.join("|"), redirects: "1" });
    const redirects = new Map((r.query.redirects ?? []).map((x) => [x.to, x.from]));
    for (const p of Object.values(r.query.pages)) {
      const text = p.revisions?.[0]?.slots?.main?.["*"];
      if (text) out.set(redirects.get(p.title) ?? p.title, text);
    }
  }
  return out;
}

const episodes = (await getJson(`https://api.tvmaze.com/shows/${SHOW_ID}/episodes`)).filter((e) => e.type === "regular");
const known = await categoryTitles();
const pageOf = (name) => known.get(name.toLowerCase()) ?? known.get(`${name} (episode)`.toLowerCase()) ?? name;
const texts = await wikitexts([...new Set(episodes.map((e) => pageOf(e.name)))]);

const missing = [];
const rows = episodes.map((e) => {
  const page = pageOf(e.name);
  const wt = texts.get(page) ?? "";
  const blurb = [synopsisParam(wt, "btvshow"), synopsisParam(wt, "btvhide")].filter(Boolean).join(" ")
    || synopsisParam(wt, "abc")
    || section(wt, "Synopsis", "Plot")
    || plain(e.summary ?? "");
  const recap = synopsisParam(wt, "recap") || section(wt, "Episode Recap", "Recap", "Plot");
  if (!wt) missing.push(e.name);
  return {
    id: `S${e.season}E${String(e.number).padStart(2, "0")}`,
    season: e.season,
    number: e.number,
    title: e.name,
    airdate: e.airdate,
    image: e.image?.medium ?? null,
    still: e.image?.original ?? null,
    tvmaze: e.url,
    wiki: wt ? `https://blueypedia.fandom.com/wiki/${encodeURIComponent(page.replace(/ /g, "_"))}` : null,
    plot: clip(recap && recap !== blurb ? `${blurb} ${recap}` : blurb, PLOT_CHARS),
  };
});

await mkdir("data", { recursive: true });
await writeFile("data/episodes.json", JSON.stringify({ built: new Date().toISOString(), sources: ["api.tvmaze.com", "blueypedia.fandom.com"], episodes: rows }, null, 1) + "\n");
// What the page displays: no plots.
await mkdir("public", { recursive: true });
await writeFile("public/episodes.json", JSON.stringify(rows.map(({ id, season, number, title, airdate, image, still }) => ({ id, season, number, title, airdate, image, still }))) + "\n");
console.log(`${rows.length} episodes, ${rows.length - missing.length} with Blueypedia plots, ~${Math.round(rows.reduce((n, r) => n + r.plot.length, 0) / 4)} plot tokens`);
if (missing.length) console.log("no wiki page:", missing.join(", "));
