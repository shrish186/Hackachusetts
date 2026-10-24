# Fathom Backend

FastAPI service for the Fathom ocean decision copilot. Deterministic risk and
routing logic lives under `app/engine/`; the LLM agent under `app/agent/` only
orchestrates tools and explains results.

## Layout

```
backend/app/
  main.py      # FastAPI app + CORS + router wiring
  api/         # HTTP endpoints (health, meta, …)
  engine/      # deterministic risk + routing (no LLM)
  agent/       # tool-calling LLM agent
  ingest/      # data ingest + caching jobs
  models/      # pydantic data models
```

## Run

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Then visit:
- Health: http://localhost:8000/api/health
- Sources: http://localhost:8000/api/meta/sources
- Docs: http://localhost:8000/docs

CORS is open to the Vite dev server at `http://localhost:5173`.

## Demo mode

Set `FATHOM_DEMO_MODE=true` to run from bundled snapshots in `/data/snapshots`
with no live network calls. The `/api/meta/sources` response reports the flag.

> Never commit `.env` or API keys. Use `.env.example` for names only.
