// One-time pull of the official pt-BR episode titles and synopses from Apple TV Brazil.
// Uses the same (undocumented, no-login) API the public show page calls; the page carries the keys.
// Output: data/sources/appletv-br.json. Run: node scripts/pull-appletv.mjs
import { writeFile, mkdir } from "node:fs/promises";

const SHOW = "umc.cmc.3ez94w3cvm4oeo9rugqsu6dx1";
const UA = "Mozilla/5.0 (bluey-finder family fan project)";

const page = await (await fetch(`https://tv.apple.com/br/show/bluey/${SHOW}`, { headers: { "User-Agent": UA } })).text();
const utsk = page.match(/utsk":"([^"]+)/)?.[1];
const utscf = page.match(/utscf":"([^"]+)/)?.[1];
if (!utsk || !utscf) throw new Error("keys not found on the show page");

const episodes = [];
for (let offset = 0; ; offset += 50) {
  const q = new URLSearchParams({ caller: "web", sf: "143503", locale: "pt-BR", v: "100", pfm: "web", utscf, utsk, nextToken: `${offset}:50` });
  const res = await fetch(`https://uts-api.itunes.apple.com/uts/v3/shows/${SHOW}/episodes?${q}`, { headers: { "User-Agent": UA } });
  if (!res.ok) throw new Error(`${res.status} at offset ${offset}`);
  const { data } = await res.json();
  episodes.push(...data.episodes.map((e) => ({
    season: e.seasonNumber,
    number: e.episodeNumber,
    title: e.title,
    description: e.description ?? "",
    released: e.releaseDate ? new Date(e.releaseDate).toISOString().slice(0, 10) : null,
    url: e.url,
  })));
  if (data.episodes.length < 50 || episodes.length >= data.totalEpisodeCount) break;
  await new Promise((r) => setTimeout(r, 500));
}

await mkdir("data/sources", { recursive: true });
await writeFile("data/sources/appletv-br.json", JSON.stringify({ pulled: new Date().toISOString(), source: `https://tv.apple.com/br/show/bluey/${SHOW}`, episodes }, null, 1) + "\n");
const perSeason = episodes.reduce((m, e) => ({ ...m, [e.season]: (m[e.season] ?? 0) + 1 }), {});
console.log(`${episodes.length} episodes`, perSeason);
