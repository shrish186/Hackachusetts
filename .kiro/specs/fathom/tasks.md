# Fathom — Implementation Plan

> Put this file at `.kiro/specs/fathom/tasks.md`. In Kiro, open it and click **Start task** next to each item.

**Team (4 people, rename as needed)**
- **A: Data & Geo** (ingest, grid, zones, risk model)
- **B: Backend & Agent** (FastAPI, routing, MCP server, agent)
- **C: Frontend & Map** (React, MapLibre, deck.gl)
- **D: Product, QA & Story** (simulator logic, tests, brief export, pitch, demo)

Assumes ~30 hours. If you have less, drop everything marked **[stretch]** and shrink Phase 3.

---

## Phase 0 — Setup and reality check (hours 0–2) — everyone

- [ ] 0.1 Open the Hackachusetts C4/C5 starter zip and dataset links; list what you actually got **(A, D)**
- [ ] 0.2 Create repo, copy `.kiro/specs/fathom/*` and `.kiro/steering/*` into it, commit **(D)**
- [ ] 0.3 Data reality check: for every source in design.md §3, confirm access from a laptop, download a snapshot, note any gaps **(A)** *(Req 10)*
- [ ] 0.4 Scaffold: `/backend` (FastAPI), `/frontend` (Vite React TS), `/data`, `/config` **(B, C)**
- [ ] 0.5 Decide the study-area bbox and grid resolution from the data you actually have **(A)**
- [ ] 0.6 Confirm LLM access (Bedrock or other) and put keys in `.env` (never commit) **(B)**

## Phase 1 — Vertical slice: map + zones + risk (hours 2–10)

- [ ] 1.1 Build land mask and grid generator; unit test land cells **(A)** *(Req 5.1)*
- [ ] 1.2 Ingest and normalize zones into `Zone` objects with source URLs and dates **(A)** *(Req 2)*
- [ ] 1.3 Ingest buoy and forecast data into `Conditions`; implement cache + "cached" flag **(A)** *(Req 1.3)*
- [ ] 1.4 Implement whale risk model + `config/risk.yaml` **(A)** *(Req 3)*
  - [ ] 1.4.1 Property tests: monotonic in speed, bounded [0,1], sightings never lower risk
- [ ] 1.5 FastAPI endpoints for layers (conditions, zones, risk, meta/sources) **(B)** *(Req 1, 2, 3)*
- [ ] 1.6 Frontend shell: MapLibre map, layer toggles, time slider, data timestamp strip **(C)** *(Req 1)*
- [ ] 1.7 Render zones with click popups and inactive dimming **(C)** *(Req 2.2, 2.3)*
- [ ] 1.8 Render risk heatmap (deck.gl) with speed slider and per-cell factor breakdown **(C)** *(Req 3.4)*
- [ ] 1.9 **Checkpoint:** live or cached map shows conditions, zones, and risk. Demo it internally. **(all)**

## Phase 2 — Routing + agent (hours 10–20)

- [ ] 2.1 Cost grid builder with 3-hour time slices **(B)** *(Req 5)*
- [ ] 2.2 A* router with zone speed caps, prohibited zones, weather limits **(B)** *(Req 5.1, 5.2)*
  - [ ] 2.2.1 Property tests: never crosses land, never enters prohibited active zone
  - [ ] 2.2.2 Golden tests for 3 fixed trips
- [ ] 2.3 Alternates via `risk_pref` sweep + de-dupe; "no legal route" explanation **(B)** *(Req 5.3, 5.4)*
- [ ] 2.4 Fuel and ETA estimators (labeled estimates) **(B)**
- [ ] 2.5 Build `fathom-mcp` server exposing tools from design.md §7; register it in `.kiro/settings/mcp.json` so Kiro can use it too **(D)**
- [ ] 2.6 Agent loop with tool calling, 8-call cap, SSE streaming of tool events **(B)** *(Req 4.5)*
- [ ] 2.7 Citation guard: strip or re-prompt uncited numbers; evals for 10 prompts **(D)** *(Req 4.3, 4.4)*
- [ ] 2.8 Captain UI: request panel, streaming tool-call feed, ranked plan cards with route on map **(C)** *(Req 4)*
- [ ] 2.9 Plan card "why" drawer (zones crossed, risk summary, weather window, citations) **(C)** *(Req 4.2)*
- [ ] 2.10 **Checkpoint:** type a trip request, get 2–3 routes with cited explanation. **(all)**

## Phase 3 — Simulator + polish (hours 20–28)

- [ ] 3.1 Build fleet sample (historical track sample or synthetic seeded from ports and grounds) **(A)** *(Req 6.1)*
- [ ] 3.2 Effort proxy grid from vessel tracks (slow speed + turning pattern = fishing) or synthetic with clear label **(A)** *(Req 6.4)*
- [ ] 3.3 `simulate_zone`: baseline vs scenario, parallel routing, cached baseline **(B, D)** *(Req 6.1)*
- [ ] 3.4 Pareto frontier + plain-language summary generator **(D)** *(Req 6.2, 6.3, 6.5)*
- [ ] 3.5 Manager UI: draw tool, scenario list, trade-off chart, summary **(C)** *(Req 6)*
- [ ] 3.6 Three preloaded scenarios: full closure, dynamic zone, seasonal speed limit **(D)**
- [ ] 3.7 Portuguese and Spanish brief generation; numbers/zone names must match across languages **(B, D)** *(Req 7)*
- [ ] 3.8 One-page brief export + trip log **(D)** *(Req 8)*
- [ ] 3.9 Advisory disclaimer, "Demo data"/"synthetic" badges everywhere relevant **(C)** *(Req 9)*
- [ ] 3.10 Demo mode: run entire flow from bundled snapshots with network off; smoke test **(B)** *(Req 10)*
- [ ] 3.11 Mobile-width pass on Captain mode **(C)**
- [ ] 3.12 **[stretch]** Wind construction overlay with per-day conflict alerts **(A)**
- [ ] 3.13 **[stretch]** Photo upload for whale/gear report assistant **(B)**

## Phase 4 — Story and rehearsal (hours 28–30+) — everyone

- [ ] 4.1 Freeze features. Only bug fixes after this point **(all)**
- [ ] 4.2 Record a backup demo video in demo mode **(D)**
- [ ] 4.3 Capture Kiro evidence: spec screenshots, steering files, hook running, MCP tool call from Kiro **(D)**
- [ ] 4.4 Build slides from `pitch.md`; rehearse 3 times with a timer **(all)**
- [ ] 4.5 Pre-load the exact demo state; test projector resolution and Wi-Fi fallback **(C, D)**

---

## Phase 5 — Ship it (before the deadline) — everyone

- [ ] 5.1 Deploy the app to a public URL and test it in a private browser window **(B, C)**
- [ ] 5.2 Write README: what it does, how to run locally, how to test, data sources **(D)**
- [ ] 5.3 Fill in KIRO_WRITEUP.md with real screenshots and real numbers **(all)**
- [ ] 5.4 Confirm `.kiro/` is committed and NOT in `.gitignore` **(D)**
- [ ] 5.5 Record the demo video: under 3 minutes, public on YouTube/Vimeo, no copyrighted music, no third-party logos **(D, C)**
- [ ] 5.6 Submit the form: video link, repo URL, track (Climate Tech & Clean Energy), description, Kiro write-up, test instructions **(Representative)**

---

## Who does what, if someone is blocked

- Data blocked → switch that layer to synthetic seed, label it, move on.
- Routing slow → coarser grid; reduce fleet to 100 trips.
- Agent flaky → ship deterministic plan cards first; agent narrative second.
- Behind schedule at hour 20 → skip Phase 3 stretch + Portuguese/Spanish exports; keep the simulator, because it is your differentiator.
