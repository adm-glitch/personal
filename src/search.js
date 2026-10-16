// One Jev request per query, following TypeSafe's "line-by-line search" recipe:
// the state is the whole episode catalogue (unchanged between searches), one Choice ranks every
// episode id against the query, and one Noul says whether any episode matches at all.
const ENDPOINT = "https://api.typesafe.ai/v1/systemone";

export function catalogue(episodes) {
  return episodes.map((e) => `${e.id} | ${e.title} | ${e.plot}`).join("\n");
}

export function buildRequest(episodes, state, query, model = "jev-latest") {
  const memory = query.trim().slice(0, 200);
  return {
    model,
    state,
    questions: {
      episode: {
        type: "choice",
        instructions: {
          memory,
          question:
            "A parent or child is trying to find a Bluey episode from a vague memory of it, written in `memory` " +
            "(often in Brazilian Portuguese, sometimes a title, a scene, a place, a game or a feeling). " +
            "Which episode in the catalogue are they thinking of?",
        },
        criteria: Object.fromEntries(episodes.map((e) => [e.id, null])),
      },
      exists: {
        type: "noul",
        instructions: { memory, question: "Does at least one episode in the catalogue match `memory`?" },
        criteria: { true: "An episode clearly contains what is described", false: "No episode is about this" },
      },
    },
  };
}

export async function searchJev({ apiKey, episodes, state, query, model, signal }) {
  const started = Date.now();
  const res = await fetch(ENDPOINT, {
    method: "POST",
    headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
    body: JSON.stringify(buildRequest(episodes, state, query, model)),
    signal,
  });
  if (!res.ok) throw new Error(`jev ${res.status}: ${(await res.text()).slice(0, 300)}`);
  const body = await res.json();
  const probs = body.answers.episode.probabilities;
  const ranked = Object.entries(probs)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8)
    .map(([id, p]) => ({ id, p: Math.round(p * 1000) / 1000 }));
  return {
    results: ranked,
    exists: body.answers.exists.noul,
    confidence: body.answers.episode.confidence,
    model: body.model,
    tokens: body.usage?.input_tokens,
    ms: Date.now() - started,
  };
}
