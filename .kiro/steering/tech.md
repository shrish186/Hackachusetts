---
inclusion: always
---
# Tech
- Backend: Python 3.11, FastAPI, pydantic v2, numpy, shapely, geopandas, xarray, pytest + hypothesis.
- Frontend: React + Vite + TypeScript, MapLibre GL, deck.gl, Tailwind.
- Agent: tool-calling loop, max 8 tool calls, SSE streaming of tool events.
- Risk/route logic is deterministic Python. Never put risk, routing, or zone logic inside prompts.
- Parameters live in /config/*.yaml, never hardcoded.
- All times UTC internally; display in America/New_York.
- Every dataset has: source_url, fetched_at, and a cached/synthetic flag.

## Style
- Type hints everywhere. Small pure functions. Docstrings state units (knots, meters, hours).
- Tests reference the requirement number they cover in the test name, e.g. `test_req3_risk_monotonic_in_speed`.
- Property-based tests (Hypothesis) for every invariant listed in design.md section 12.

## Keep it demoable
- The whole app must run with `FATHOM_DEMO_MODE=true` using only files in /data/snapshots.
- Prefer a small working thing over a big broken thing. Commit often.
