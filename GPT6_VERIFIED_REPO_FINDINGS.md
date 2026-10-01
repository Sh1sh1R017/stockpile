# VERIFIED REPOSITORY FINDINGS FOR GPT-6

These are evidence-backed observations from the current `main` scan. Treat them as starting evidence, not as an exhaustive audit. GPT-6 must trace each to runtime behavior and inspect adjacent code before patching.

## Finding 1 — Frontend duplicate campaign key warning

Observed runtime error:
`Encountered two children with the same key, capcut_podcast_pro.`

Location reported by the running Next.js app:
`web/app/page.tsx`, campaign `<option>` map.

Relevant implementation:
`campaigns.map((c) => <option key={c.id} value={c.id}>...)`

The backend campaign registry currently registers `capcut_podcast_pro` once and returns `list(self._campaigns.values())`, so the duplicate is NOT explained by an obvious duplicate dictionary registration in `ai_broll_autopilot/campaigns/registry.py`.

Required investigation:
- inspect `/api/campaigns` response at runtime
- trace frontend state population
- inspect any client-side merge/append behavior
- verify whether duplicate API responses can occur across fetches
- fix the source of duplication
- do NOT mask it with an index-based React key

## Finding 2 — CORS configuration is overly permissive

`ai_broll_autopilot/api/app.py` configures FastAPI CORS with:
- `allow_origins=["*"]`
- `allow_credentials=True`
- `allow_methods=["*"]`
- `allow_headers=["*"]`

This is an overly broad production security configuration and must be reviewed against the actual deployment model. GPT-6 should determine the intended frontend/backend origins and replace wildcard access with an explicit allowlist where appropriate, while preserving local development.

## Finding 3 — Repo contains deterministic-rendering guidance that explicitly forbids Math.random, but runtime tooling contains Math.random

The repository's own Remotion/rendering guidance repeatedly states deterministic rendering should avoid `Math.random`. Separately, `.agents/skills/erduo-broll-loop-engineering/scripts/lean-render.mjs` uses `Date.now()` and `Math.random()` to create temporary filenames.

This is NOT automatically a rendering correctness bug because the usage shown is for unique temporary filenames rather than frame output. GPT-6 should distinguish harmless filesystem entropy from render-state randomness and must not remove it merely because a search found the token.

## Finding 4 — Large mixed-responsibility frontend surface needs audit

`web/app/page.tsx` is a very large client component managing jobs, upload/import, campaigns, B-roll swapping, cutaway insertion, memes, subtitles, BGM, HDR, OpenReel, diffusion, feedback, and timeline/editor interactions. It also dynamically imports multiple heavy modals.

This is an architecture/performance risk rather than proof of a bug. GPT-6 should inspect effect dependencies, fetch orchestration, rerender frequency, state ownership, and whether unrelated feature state causes expensive dashboard rerenders.

## Finding 5 — API server contains many global/shared service instances

`ai_broll_autopilot/api/app.py` creates module-level instances including the database, learning engine, orchestrator, HDR task dictionary, and several imported singleton services.

This may be intentional, but GPT-6 should audit concurrency, process-local state, multi-worker behavior, task lifetime, and whether state such as HDR tasks or queue state is lost/repeated when multiple API workers run.

## REQUIRED FOLLOW-UP

For each finding, GPT-6 must:
1. inspect the exact source and call graph;
2. reproduce or logically prove the defect;
3. classify severity and confidence;
4. propose the smallest fix;
5. add a regression test where feasible;
6. verify that the fix does not break existing Stockpile features.
