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

Live demo: https://fathom-six-vert.vercel.app (API: https://hackachusetts.onrender.com/api/health). First load can take up to a minute while the free server wakes.

Demo mode is on, and there is no login.

## Judge quickstart

1. Open https://fathom-six-vert.vercel.app. If nothing loads at first, wait up to a minute while the free API server wakes.
2. Click **Try the demo trip** (Gloucester, small boat, 9 kn, whale-season replay on 15 March 2026).
3. Compare the plan cards, sorted Fastest, Balanced, Safest. Open one card's "why" drawer to see zones, weather and citations.
4. Switch to **Manager**, run a preset scenario, and read the risk-versus-cost trade-off.
5. Switch the language to **PT**, then **ES**. The numbers and zone names stay the same.

## Known limitations

- **Zone shapes are hand-drawn approximations** of the official NOAA and BOEM areas. The dates and rules come from the official sources, but the polygons are not survey-accurate. Do not use them for navigation.
- **Whale data is 60 real historical sightings** from OBIS, for January to May inside the study area. They are not live detections, so the risk layer is a screening estimate, not a measured strike probability.
- **Advisory only.** Fathom does not replace official notices, VHF warnings, or a captain's judgment. Fuel, the effort proxy and the fleet are estimates or synthetic, and are labelled that way.
- **Free-tier cold start.** The API runs on Render's free plan, which sleeps when idle. The first request after a pause can take up to a minute. After `/api/ready` returns 200, plans are fast.
- **Jeffreys Ledge is closed in the replay.** On 15 March 2026 it sits inside the Western Gulf of Maine seasonal closure, so trips there show "access lost" with the nearest open water.

## How to test (for judges)

1. Open https://fathom-six-vert.vercel.app. If the first load is slow, the free API server is waking up; wait up to a minute.
2. In Captain mode, click **Try the demo trip** (Gloucester, small boat, 9 kn), then plan it. Watch the live tool-call feed, then compare the 2 or 3 ranked plan cards (Fastest, Balanced, Safest) on the map. Open a card's "why" drawer to see the zones crossed, weather window and citations.
3. Switch to **Manager** mode, pick a scenario (for example the seasonal 10 kn speed limit) and run it. Compare risk removed against the cost to the fleet on the trade-off chart, and read the plain-language summary.
4. Switch the language to **PT** and then **ES**. Numbers and zone names stay the same in every language.
5. Optional: print or save the one-page trip brief from a plan card.

To check the API directly: `GET https://hackachusetts.onrender.com/api/health` (alive) and `/api/ready` (warm-up finished).

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

Key API endpoints: `GET /api/health`, `GET /api/ready`,
`GET /api/layers/{conditions,zones,risk}`, `GET /api/sim/scenarios`,
`POST /api/sim/run`, `GET /api/meta/sources`, `POST /api/trip/plan` (SSE agent
stream), `POST /api/trip/brief`. Full shapes: [docs/API_CONTRACT.md](docs/API_CONTRACT.md).
Interactive docs (`/docs`) are off unless `FATHOM_ENABLE_DOCS=true`.
Deployment: [docs/DEPLOY.md](docs/DEPLOY.md).

## Run the tests

```bash
cd backend && pytest -q          # includes Hypothesis property-based tests
ruff check --isolated --select E4,E7,E9,F --target-version py311 backend mcp   # from the repo root
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

- Vidhaan Kothari
- Shrish
- Anant
- Aayush

## License and credits

MIT, see [LICENSE](LICENSE). Data, map and library credits: [ATTRIBUTIONS.md](ATTRIBUTIONS.md).
