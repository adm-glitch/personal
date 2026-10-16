# Qual episódio? — Bluey finder

Type whatever you remember about a Bluey episode ("o do pacote", "câmera na loja") and get the season and
episode number, so you can find it on the TV. Family fan project.

## How it works
- `scripts/build-episodes.mjs` pulls every episode from the TVMaze API (title, number, still) and its plot from
  Blueypedia (MediaWiki API) into `data/episodes.json`, and a plot-free copy into `public/episodes.json`.
- `src/worker.js` (Cloudflare Worker) answers `GET /api/search?q=` with one Jev request
  (`src/search.js`): the state is the whole episode catalogue, a Choice ranks all 153 episode ids against the
  query, and a Noul says whether anything matches. ~0.5 s, ~29k input tokens (≈ $0.001) per search, cached at the
  edge for a day, 20 searches/min per IP.
- `public/` is the page: instant local title matches while typing, Jev ranking 350 ms after you stop.
- Plots are sent to Jev only; the page shows number, title and still.

## Run
```bash
npm install
npm run data                                   # rebuild the episode list
doppler run -p mauricio-friday -c prd -- npm run try      # test queries against Jev
CLOUDFLARE_INCLUDE_PROCESS_ENV=true doppler run -p mauricio-friday -c prd --only-secrets TYPESAFE_API_KEY -- npm run dev
npx wrangler secret put TYPESAFE_API_KEY       # once, before the first deploy
npm run deploy
```

## Credits
Episode data and images: [TVMaze](https://www.tvmaze.com/shows/41821/bluey) (CC BY-SA). Plots used for search:
[Blueypedia](https://blueypedia.fandom.com) (CC BY-SA). Search: [Jev](https://typesafe.ai) by TypeSafe.
Bluey © Ludo Studio; this project is not affiliated with Ludo Studio, BBC Studios or Disney.
