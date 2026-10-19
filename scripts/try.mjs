// Runs test queries against Jev and checks the expected episode is on top.
// Run: doppler run -p mauricio-friday -c prd -- node scripts/try.mjs ["one query"]
import { readFile } from "node:fs/promises";
import { catalogue, searchJev } from "../src/search.js";

const all = JSON.parse(await readFile(new URL("../data/episodes.json", import.meta.url))).episodes;
// TRY_PLOT_CHARS=300 tests a shorter catalogue (faster, maybe less accurate).
const max = Number(process.env.TRY_PLOT_CHARS) || Infinity;
const episodes = all.map((e) => ({ ...e, plot: e.plot.slice(0, max) }));
const state = catalogue(episodes);
const byId = new Map(episodes.map((e) => [e.id, e]));

const CASES = [
  ["o episódio do pacote", "S3E14"],
  ["festa de aniversário, passa o pacote, a Bingo nunca ganha", "S3E14"],
  ["câmera de segurança na loja", "S3E45"],
  ["dançando na farmácia na TV", "S3E45"],
  ["store tv camera dancing", "S3E45"],
  ["xilofone mágico que congela o pai", "S1E01"],
  ["casamento da irmã", "S3E49"],
  ["a noiva foge do casamento", "S3E49"],
  ["dinossauro de pelúcia no espaço sideral com foguete", null],
];

const queries = process.argv[2] ? [[process.argv[2], null]] : CASES;
let hits = 0;
for (const [query, expected] of queries) {
  const r = await searchJev({ apiKey: process.env.TYPESAFE_API_KEY, episodes, state, query });
  const top = r.results.slice(0, 3).map((x) => `${x.id} ${byId.get(x.id).title} ${x.p}`).join(" · ");
  const ok = expected ? r.results[0].id === expected : null;
  if (ok) hits++;
  console.log(`${ok === null ? "  " : ok ? "✓ " : "✗ "}"${query}" → ${top} | exists ${r.exists.toFixed(2)} | ${r.ms} ms, ${r.tokens} tok`);
}
const expectedCount = queries.filter((q) => q[1]).length;
if (expectedCount) console.log(`${hits}/${expectedCount} top-1`);
