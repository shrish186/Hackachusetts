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
- **Our own `fathom` MCP server** (`mcp/fathom_mcp/`) exposes all **eight**
  engine tools (`get_conditions`, `get_zones`, `get_whale_risk`, `plan_routes`,
  `get_effort_proxy`, `estimate_fuel`, `simulate_zone`, `export_brief`). They are
  wired to the real backend via `backend_bridge.py`, degrade to labelled
  placeholders if the backend isn't importable, and `python -m fathom_mcp` boots
  clean, so the server is enabled in `.kiro/settings/mcp.json`. The in-app agent
  and Kiro call the *same* tested engine. Screenshot: `08-mcp-fathom.png`.

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

`pytest -q`: **112 tests pass** across 15 test files.

## 7. Real bugs QA caught (and what happened)

- **Simulator timeout / 504 (fixed).** `POST /api/sim/run` with a preset took
  >20 s on Render and returned `504 {"error":"Request timed out."}`; a second
  call hung 45 s+. Cause: the live A* router ran over the 200-trip fleet four
  times per request. Fix: precompute the three presets at build time into
  `data/snapshots/sim_results.json` (`scripts/precompute_sim.py`) and serve them
  in ~20 ms; keep the live path only for custom polygons, now bounded (vertex
  cap 200, study-area clip, hard 8 s budget → `422`, single-flight semaphore →
  `429`). Commit `7951075`.
- **Reversed departure-window 500.** A `depart_window` with end before start
  surfaced a 500 instead of a clean 422 — logged for the API owner; the trip
  request model should reject it at validation.
- **Blank-map worker bug.** The map tile/worker init intermittently rendered a
  blank map on first load — a frontend (Lane C) issue tracked during QA.

Honesty: only the 504 has a committed fix in this repo; the other two are QA
findings handed to their owning lanes.

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
