# Fathom

**An ocean decision copilot for Massachusetts' working waterfront.** Fathom fuses open weather, regulatory-zone, and whale-risk data so that:

- **Captain Joe (fisherman)** can describe a trip in plain language and get 2-3 safe, ranked routes with cited explanations, in English, Portuguese, or Spanish.
- **Dana (harbor / fisheries manager)** can draw a proposed protection zone and instantly see how much whale risk it removes versus what it costs the fleet.

Hackachusetts 2026 track: **Climate Tech & Clean Energy** (blue economy and ocean protection).
Built with **Kiro** (spec-driven). See [KIRO_WRITEUP.md](KIRO_WRITEUP.md) and the [`.kiro/`](.kiro) folder.

> Advisory only. Fathom does not replace official NOAA notices, VHF warnings, or a captain's judgment. Demo uses public or clearly-labeled synthetic data.

## Live demo
TODO: paste deployed URL here. Demo mode is on by default, no login needed.

## Run it locally
```bash
cp .env.example .env            # demo mode needs no keys, the agent needs one LLM key
# backend
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
# frontend (new terminal)
cd frontend && npm install && npm run dev
```
Open http://localhost:5173

## Run the tests
```bash
cd backend && pytest -q          # includes Hypothesis property-based tests
```

## How it is built
- Deterministic Python engine for whale risk and routing (no LLM does the math).
- LLM agent calls the engine through an MCP server and must cite every claim.
- React + MapLibre + deck.gl front end.
- Full spec in `.kiro/specs/fathom/` (requirements, design, tasks).

## Data sources
See `data/snapshots/SOURCES.md` for every dataset, its URL, fetch time, and whether it is live, cached, or synthetic.

## Team
TODO: four names.
