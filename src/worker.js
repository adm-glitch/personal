// Cloudflare Worker: serves the static page from public/ and answers GET /api/search?q=...
// The TypeSafe key stays here (secret TYPESAFE_API_KEY); the browser never sees it.
import data from "../data/episodes.json";
import { catalogue, searchJev } from "./search.js";

const STATE = catalogue(data.episodes);
const MIN_CHARS = 3;
const MAX_CHARS = 200;

const json = (body, status = 200, extra = {}) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", ...extra },
  });

async function search(request, env, ctx) {
  const url = new URL(request.url);
  const q = (url.searchParams.get("q") ?? "").replace(/\s+/g, " ").trim().toLowerCase();
  if (q.length < MIN_CHARS) return json({ results: [], exists: 0 });
  if (q.length > MAX_CHARS) return json({ error: "query too long" }, 400);

  // Same query, same answer: cache it at the edge for a day.
  const cacheKey = new Request(`${url.origin}/api/search?q=${encodeURIComponent(q)}`);
  const cache = caches.default;
  const hit = await cache.match(cacheKey);
  if (hit) return hit;

  if (env.LIMITER) {
    const ip = request.headers.get("CF-Connecting-IP") ?? "unknown";
    const { success } = await env.LIMITER.limit({ key: ip });
    if (!success) return json({ error: "slow down" }, 429);
  }

  try {
    const r = await searchJev({ apiKey: env.TYPESAFE_API_KEY, episodes: data.episodes, state: STATE, query: q });
    const res = json({ results: r.results, exists: r.exists, ms: r.ms }, 200, { "Cache-Control": "public, max-age=86400" });
    ctx.waitUntil(cache.put(cacheKey, res.clone()));
    return res;
  } catch (err) {
    console.error(String(err));
    return json({ error: "search unavailable" }, 502);
  }
}

export default {
  async fetch(request, env, ctx) {
    const { pathname } = new URL(request.url);
    if (pathname === "/api/search") return search(request, env, ctx);
    return env.ASSETS.fetch(request);
  },
};
