// Runs test queries against Jev and checks the expected episode comes first (and in the top 3).
// Run: doppler run -p mauricio-friday -c prd -- node scripts/try.mjs ["one query"]
// TRY_MODE=plots   English plots only (the first version), clipped to TRY_PLOT_CHARS (default 700)
// TRY_MODE=cards   pt-BR cards only (default when cards exist)
// TRY_MODE=both    pt-BR cards + the first TRY_PLOT_CHARS (default 250) of the English plot
import { readFile } from "node:fs/promises";
import { catalogue, searchJev } from "../src/search.js";

const all = JSON.parse(await readFile(new URL("../data/episodes.json", import.meta.url))).episodes;
const mode = process.env.TRY_MODE ?? (all.some((e) => e.card) ? "cards" : "plots");
const plotChars = Number(process.env.TRY_PLOT_CHARS) || (mode === "both" ? 250 : 700);
const episodes = mode === "plots"
  ? all.map(({ card, ...e }) => ({ ...e, plot: e.plot.slice(0, plotChars) }))
  : all;
const state = catalogue(episodes, { plotChars: mode === "both" ? plotChars : 0 });
const byId = new Map(episodes.map((e) => [e.id, e]));

// The first block was used to brief the card writers; the second was not.
const CASES = [
  ["o episódio do pacote", "S3E14"],
  ["câmera de segurança na loja", "S3E45"],
  ["dançando na farmácia na TV", "S3E45"],
  ["casamento da irmã", "S3E49"],
  ["a noiva foge do casamento", "S3E49"],
  // unseen by the card writers
  ["festa de aniversário, a Bingo nunca ganha", "S3E14"],
  ["store tv camera dancing", "S3E45"],
  ["xilofone mágico que congela o pai", "S1E01"],
  ["o do balão que não pode cair no chão", "S1E03"],
  ["as velhinhas que dançam", "S1E28"],
  ["o pai fica grávido de mentira", "S2E13"],
  ["a bingo dorme e sonha que vai pro espaço", "S2E26"],
  ["loja de ferramentas gigante", "S2E02"],
  ["acampamento e o amigo francês", "S1E43"],
  ["aprendendo a andar de bicicleta", "S1E11"],
  ["esperando a comida chinesa ficar pronta", "S1E14"],
  ["morcego comendo fruta", "S1E08"],
  ["dinossauro de pelúcia no espaço sideral com foguete", null],
];

const queries = process.argv[2] ? [[process.argv[2], null]] : CASES;
let top1 = 0, top3 = 0, ms = 0;
for (const [query, expected] of queries) {
  const r = await searchJev({ apiKey: process.env.TYPESAFE_API_KEY, episodes, state, query });
  ms += r.ms;
  const top = r.results.slice(0, 3).map((x) => `${x.id} ${byId.get(x.id).pt ?? byId.get(x.id).title} ${x.p}`).join(" · ");
  const rank = expected ? r.results.findIndex((x) => x.id === expected) : null;
  if (rank === 0) top1++;
  if (rank !== null && rank >= 0 && rank < 3) top3++;
  const mark = rank === null ? "  " : rank === 0 ? "✓ " : rank > 0 && rank < 3 ? "~ " : "✗ ";
  console.log(`${mark}"${query}" → ${top} | exists ${r.exists.toFixed(2)} | ${r.ms} ms`);
}
const n = queries.filter((q) => q[1]).length;
if (n) console.log(`[${mode}] top-1 ${top1}/${n} · top-3 ${top3}/${n} · avg ${Math.round(ms / queries.length)} ms · state ~${Math.round(state.length / 4 / 1000)}k tok`);
