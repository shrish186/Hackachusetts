# Submission text

## Feature description (~250 words)

Fathom is an ocean decision copilot for Massachusetts' working waterfront. In
Massachusetts waters, right whales, fishing closures, slow zones, offshore wind,
and fast-changing weather all collide — and the people affected have to make
decisions with scattered data. Fathom gives them one trusted picture.

For a fisherman, it turns a plain-language request ("leaving Gloucester at 5am,
12-hour trip, small boat, 9 knots, fish near Stellwagen, safest option") into
2–3 ranked routes that avoid closures, respect slow-zone speed limits, and weigh
whale risk against time — each with a cited "why" and a printable brief in
English, Portuguese, or Spanish.

For a harbor or fisheries manager, Fathom's what-if simulator re-routes a
representative fleet around a candidate protection zone and reports the
trade-off: how much whale risk is removed versus the cost in steaming hours,
fuel, and access to fishing grounds. It compares options on a Pareto frontier,
so a seasonal speed limit that removes most of the risk at a fraction of a
closure's cost is visible at a glance.

The engineering point: the LLM never computes risk, routes, or zone facts. A
deterministic, tested Python engine does — seasonal presence, sighting recency,
and a published speed-lethality curve. The agent only calls tools and must cite
every claim; uncited facts are stripped. The same engine is exposed as an MCP
server that Kiro itself used while building the project. Everything runs in a
demo mode from bundled public/synthetic data, with synthetic layers clearly
labeled.

## Testing instructions

**Run the demo (no keys needed):**

```bash
# backend
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000   # FATHOM_DEMO_MODE=true by default
# frontend (new terminal)
cd frontend && npm install && npm run dev    # open http://localhost:5173
```

**Try the Captain flow:** open Captain mode, click "Try the demo trip," watch the
agent stream tool calls, open "why" on a plan to see citations, slide the
risk preference, switch the language (numbers stay identical).

**Try the Manager flow (the simulator):**

```bash
curl http://localhost:8000/api/sim/scenarios
curl -X POST http://localhost:8000/api/sim/run \
  -H 'Content-Type: application/json' \
  -d '{"scenario_id":"seasonal_speed_limit"}'
```

The response includes the baseline, per-option percent deltas, an `on_frontier`
flag, and trilingual summaries with identical numbers.

**Run the automated tests:**

```bash
cd backend && pytest -q    # engine + API + Hypothesis property tests
```

**MCP server (optional):** `cd mcp && pip install -e . && python -m fathom_mcp`
starts the stdio server; tools return real engine data when the backend is on
the path, else clearly-labeled placeholders.
