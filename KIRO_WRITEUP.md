# How we used Kiro to build Fathom

Every number here is pulled from the repo (`pytest -q`, `tasks.md`,
`.kiro/`, git history). Screenshot placeholders use the exact filenames from
`docs/kiro-evidence/README.md`; drop the PNGs in that folder before submitting.

## 1. Which Kiro tools did we use?

- **Kiro CLI** — primary driver for Lane D (simulator, agent, MCP, QA, docs):
  committing after each task, `git pull --rebase --autostash` before every push.
- **Kiro Web** — Lanes A and B (data ingest, risk model, API, agent, hardening).
- **Kiro IDE** — initial project setup: spec, steering, hooks, and MCP config.

We ran four parallel lanes against one shared `main`; the interleaved git
history (e.g. `Lane A (5,6,9)…`, `Lane B task 7…`, `Lane C task 4…`) and the
strict file ownership in `.kiro/steering/structure.md` are what kept four people
from colliding. Screenshot: `10-cli-or-web.png`.

## 2. Spec-driven development

The spec lives in `.kiro/specs/fathom/`: **10 requirements** (EARS form) in
`requirements.md`, a 14-section `design.md`, and **52 tasks** in `tasks.md`.
Tasks are tracked by lane in git commit messages rather than checkbox ticks, so
the honest "completed" count is read from the history, not from `[x]` marks
(there are 0 ticked boxes — a process gap we'd fix next time).

Spec-driven paid off most on the **deterministic engine**: the whale-risk model
was built straight from design §5 + requirement 3, *including its invariants*,
which became property tests (see §6). Vibe coding stayed useful for UI polish
(Lane C) and copy. Screenshots: `01-spec-requirements.png`,
`02-spec-design.png`, `03-spec-tasks-running.png`, `12-vibe-vs-spec.png`.

## 3. Agent hooks

Five hooks in `.kiro/hooks/`:

- **`risk-tests-on-save`** — on changes to `backend/app/engine/**` or
  `config/risk.yaml`, runs the property tests and forbids editing tests to pass.
- **`citation-guard-on-agent-change`** — enforces that every agent sentence with
  a number/zone/date carries a `[tool:call_N]` tag. The guard is also code
  (`backend/app/agent/agent.py::citation_guard`): it drops any uncited factual
  sentence, any number not present in the cited tool result, and anything
  claiming legal compliance.
- **`plain-language-check`**, **`evidence-log-on-task-done`** (which feeds
  `docs/kiro-evidence/LOG.md`), and **`secret-scan`** (flags keys/tokens/`.env`
  on save).

Screenshots: `05-hook-fired.png`, `06-hook-caught-bug.png`.

## 4. Steering docs

Five files in `.kiro/steering/`: `product.md`, `tech.md`, `structure.md` (lane
ownership), `data-and-safety.md`, `testing-pbt.md`. The highest-impact rule was
data-and-safety's "anything not from a real source must say `synthetic: true`,"
which drove a real honesty fix (`d2bb1b7 Lane A (1.1): honesty fix — mark
hand-authored snapshots synthetic:true`) and kept the agent from ever printing
"legally compliant." Screenshot: `04-steering-list.png`.

## 5. MCP

- **`fetch` MCP** — used for the hour-0 data reality check against public
  sources. Screenshot: `07-mcp-fetch.png`.
- **Our own `fathom` MCP server** (`mcp/fathom_mcp/`) exposes **nine** engine
  tools: the eight from design §7 (`get_conditions`, `get_zones`,
  `get_whale_risk`, `plan_routes`, `get_effort_proxy`, `estimate_fuel`,
  `simulate_zone`, `export_brief`) plus **`list_ports(time)`**, which returns
  ports and fishing grounds and flags which grounds are closed at a given time
  (the same rule the router uses for `access_lost`; it shares the code the
  forthcoming `GET /api/meta/ports` will use). They are wired to the real backend
  via `backend_bridge.py`, degrade to labelled placeholders if the backend isn't
  importable, and `python -m fathom_mcp` boots clean, so the server is enabled in
  `.kiro/settings/mcp.json`. The in-app agent and Kiro call the *same* tested
  engine. Screenshot: `08-mcp-fathom.png`.

## 6. Property-based testing

Hypothesis properties (steering `testing-pbt.md`), mapped to requirements, in
`backend/tests/`:

- **Risk** (`test_risk_properties.py`, Req 3): risk ∈ [0,1]; monotonic
  non-decreasing in speed; 0 on land; adding a sighting never lowers risk.
- **Routing** (`test_routing.py`, Req 5): routes never cross land or enter
  active prohibited zones.
- **Simulator** (`test_simulator.py`, Req 6/7): no Pareto-frontier option is
  dominated; deltas consistent with totals; en/pt/es summaries carry identical
  numbers; and *"a prohibited zone never increases whale risk and is never a free
  lunch."*

That last property found a **real counterexample** this round: our first version
asserted a closure never lowers total steaming hours, and Hypothesis falsified
it — a closure that sits on a fishing ground removes those trips entirely, which
*lowers* hours. The right reading is that this is **lost access** (a cost), not a
saving, so we fixed the model (report `access_lost`) and the invariant, not the
test-to-pass. Screenshot: `09-pbt-counterexample.png`.

The agent narrative also now answers **"why not that route?"** — for each
non-recommended plan it adds one cited sentence comparing it with the
recommended plan (ETA difference, whale-risk difference, extra zones crossed),
using only numbers from the `plan_routes` result so the citation guard accepts
it, identical across EN/PT/ES.

`pytest -q`: **183 passed, 1 skipped** across 19 test files.

## 7. Real bugs QA caught (and what happened)

All five are real and traceable to commits in this repo.

- **Simulator timeout / 504 (fixed).** `POST /api/sim/run` with a preset took
  >20 s on Render and returned `504 {"error":"Request timed out."}`; a second
  call hung 45 s+. Cause: the live A* router ran over the 200-trip fleet four
  times per request. Fix: precompute the three presets at build time into
  `data/snapshots/sim_results.json` (`scripts/precompute_sim.py`) and serve them
  in ~20 ms; keep the live path only for custom polygons, now bounded (vertex
  cap 200, study-area clip, hard 8 s budget → `422`, single-flight semaphore →
  `429`). Commit `7951075`.
- **Blank-map worker bug (fixed).** The map rendered blank on first load — the
  deck.gl/MapLibre worker crashed on viewport height and the container collapsed
  to a 0-height strip. Fixed over several commits: non-interleaved deck.gl
  overlay attached only after map load, a `ResizeObserver` to keep the map sized,
  and `h-full/w-full` on the container (`7476dec`, `058af71`, `40ca948`,
  `6977637`, `b124381`).
- **CARTO API-key tiles (fixed).** The basemap went blank because CARTO's tile
  endpoint started requiring a key (and a stray `{r}` retina placeholder broke
  the URL). Fixed by switching to keyless OpenStreetMap tiles and dropping `{r}`
  (`097826b`, `7ce988f`).
- **Empty Render env vars (fixed).** The deployed backend came up with no
  `FATHOM_ALLOWED_ORIGINS`/`VITE_API_URL` set, so CORS origins and the API base
  were wrong. Fixed by documenting the required env in `docs/DEPLOY.md` and
  `render.yaml` and trimming trailing slashes/spaces on parse (`ad1b389`,
  `b860b57`).
- **CORS 405 on preflight (fixed).** The browser's `OPTIONS` preflight returned
  405, blocking the Vercel frontend from calling the API. Fixed in the CORS /
  hardening middleware with regression tests (`bc023d4`).

Honesty note: the blank-map, CARTO, Render-env and CORS fixes were made by the
frontend/backend lanes (Lane C / Lane B); Lane D (QA) reported them and owns the
simulator 504 fix.

Screenshots: `13-live-map.png` (map rendering after the fixes),
`14-manager-result.png` (Pareto result), `15-mobile-390.png` (390 px mobile),
`16-whale-season-replay.png` (the replay toggle), `17-access-lost.png` (a closed
ground reported as lost access).

## 8. Honest lessons

- **Worked:** strict lane ownership + commit-per-task + rebase-before-push kept
  four contributors on a green `main`; the deterministic-engine / LLM-explainer
  split made the agent testable and the citation guard trustworthy.
- **Did not:** cross-lane interface churn bit us — a refactor removed
  `app/api/_snapshots.py` and broke the sim import (`10233c9` hotfix), and the
  preset simulator was shipped before anyone measured its latency on the
  deployed box (hence the 504).
- **Next time:** pin cross-lane interfaces in `API_CONTRACT.md` *before* building
  dependents, measure latency in CI, and tick `tasks.md` as we go.
