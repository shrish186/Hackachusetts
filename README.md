# Fathom

**An ocean decision copilot for Massachusetts' working waterfront.** Fathom fuses
open weather, regulatory-zone, and whale-risk data so that:

- **Captain Joe (fisherman)** can describe a trip in plain language and get
  2–3 safe, ranked routes with cited explanations, in English, Portuguese, or
  Spanish.
- **Dana (harbor / fisheries manager)** can pick or draw a proposed protection
  zone and instantly see how much whale risk it removes versus what it costs the
  fleet — a measurable trade-off instead of "whales vs. jobs."

Hackachusetts 2026 — blue economy, coastal livelihoods, and ocean protection.
Built with **Kiro**, spec-driven. See [KIRO_WRITEUP.md](KIRO_WRITEUP.md) and the
[`.kiro/`](.kiro) folder.

> **Advisory only.** Fathom does not replace official NOAA notices, VHF
> warnings, or a captain's judgment. It uses public or clearly-labeled synthetic
> data; the whale-risk model is a transparent screening tool, not a prediction.

## Live demo

- App (frontend): **TODO — paste deployed URL** (demo mode on by default, no login).
- API: **TODO — paste deployed API URL** (`/api/health`, `/docs`).

## What's in the box

- **Deterministic engine (no LLM math):** whale-risk model (seasonal presence +
  sighting recency + published speed-lethality curve), a fishing-effort proxy,
  and a policy **what-if simulator** that re-routes a synthetic fleet around
  candidate zones and reports the trade-off with a Pareto frontier.
- **LLM agent** that only orchestrates tools and **cites every claim**; it never
  computes risk, routes, or zone facts.
- **MCP server** (`fathom`) exposing the engine as tools — used by the in-app
  agent and by Kiro during development.
- **React + MapLibre + deck.gl** map-first UI with Captain and Manager modes.

## Run it locally

```bash
cp .env.example .env            # demo mode needs no keys; the agent needs one LLM key
# backend
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
# frontend (new terminal)
cd frontend && npm install && npm run dev
```

Open http://localhost:5173. The frontend talks to the API via `VITE_API_URL`
(defaults to the local backend) and falls back to bundled mocks if the API is
down. `FATHOM_DEMO_MODE=true` (default) serves bundled snapshots with no network.

Key API endpoints: `GET /api/layers/{conditions,zones,risk}`,
`GET /api/sim/scenarios`, `POST /api/sim/run`, `GET /api/meta/sources`,
`POST /api/trip/plan` (SSE agent stream).

## Run the tests

```bash
cd backend && pytest -q          # includes Hypothesis property-based tests
```

CI (`.github/workflows/ci.yml`) also runs the frontend build + type-check,
`pip-audit`, `npm audit`, and a gitleaks secret scan on every push and PR.

## Data sources

See `data/snapshots/SOURCES.md` for every dataset, its URL, fetch time, and
whether it is live, cached, or synthetic. Honesty rule: anything not from a real
source is flagged `synthetic: true` in the data and badged in the UI.

## Security

See [SECURITY.md](SECURITY.md): no secrets in the repo, tool-allowlisted agent,
tool output treated as data, citation guard, and input validation.

## Team

- **Vidhaan**
- **Shrish**
- **Anant**
- **Aayush**
