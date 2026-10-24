# Fathom MCP server (`fathom_mcp`)

Exposes Fathom's **nine data/risk/route tools** (the eight from
`.kiro/specs/fathom/design.md`, section 7, plus `list_ports`) over the
[Model Context Protocol](https://modelcontextprotocol.io) using the official
`mcp` Python SDK. The same server is used two ways:

- the **in-app LLM agent** calls it at runtime to get facts it must cite;
- **Kiro** calls it during development to query the same data while writing code.

> **Status: wired to the real engine.** All nine tools now call the backend
> deterministic engine (`backend/app/engine` + `backend/app/agent/tools.py` +
> `backend/app/ingest`) through `backend_bridge.py`. When the backend package is
> importable the tools
> return real results (`placeholder: false`); if it is not (the server run fully
> standalone), each tool degrades gracefully to a clearly-labelled placeholder
> (`placeholder: true`) instead of crashing. Synthetic layers are flagged
> `synthetic: true`.

## The nine tools

| Tool | Input | Returns | Backing |
|---|---|---|---|
| `get_conditions` | bbox, time range | wave / wind / SST readings + source | `app.agent.tools.get_conditions` (NOAA NDBC snapshot) |
| `get_zones` | bbox, time | zones active/inactive + restriction + source_url | `app.ingest.zones` |
| `get_whale_risk` | bbox, time, speed_kn | risk points (0–1) + top factors per cell | `app.engine.risk` (Vanderlaan & Taggart 2007 lethality) |
| `plan_routes` | TripRequest | 2–3 `RoutePlan` objects (or "no legal route") | `app.engine.routing` (A* on the study grid) |
| `get_effort_proxy` | bbox, month | normalized effort grid (synthetic estimate) | `app.engine.effort` |
| `estimate_fuel` | route, vessel | liters + distance + hours (estimate) | `app.engine.routing` vessel burn model |
| `simulate_zone` | polygon, fleet sample id | Δrisk / Δhours / Δfuel / Δeffort %, frontier, summary | `app.engine.simulator` |
| `export_brief` | RoutePlan, language | one-page printable HTML brief | `app.api.trip.render_brief` |
| `list_ports` | time (optional) | ports + fishing grounds, each ground flagged `closed` at that time | `app.ingest.ports` + `app.ingest.zones` (shares the forthcoming `GET /api/meta/ports`) |

`get_effort_proxy` is an estimate of activity, **not** catch or revenue. A ground
is `closed` in `list_ports` when its point lies inside an active, prohibited zone
at the given time — the same rule the router uses for `access_lost`; zone dates
are real, zone polygons are hand-drawn. Nothing asserts legal compliance; the
agent/plan layer cites every number.

## Layout

```
mcp/
  pyproject.toml          # package metadata; entry point `python -m fathom_mcp`
  requirements.txt
  README.md
  fathom_mcp/
    __init__.py           # version + re-exports
    __main__.py           # `python -m fathom_mcp` -> server.main()
    server.py             # builds MCPServer / FastMCP, registers tools, runs stdio
    tools.py              # the nine tool functions (validate -> real engine / placeholder)
    backend_bridge.py     # imports the backend engine; graceful if unavailable
    models.py             # pydantic input models (bbox, time range, per-tool args)
    placeholders.py       # placeholder-response envelope (fallback only)
```

## Run

```bash
pip install -e .          # or: pip install -r requirements.txt
python -m fathom_mcp      # starts the stdio MCP server
```

`python -m fathom_mcp` is the entry point referenced by
`.kiro/settings/mcp.json`, where the `fathom` server is **enabled**
(`disabled: false`) because the server boots and the tools are wired.

## Notes for reviewers (Lane D)

- Input validation uses pydantic v2; invalid input yields a structured
  `{"error": "invalid_input", "detail": [...]}` result instead of crashing.
- The server module supports both SDK lines: v2 `MCPServer`
  (`mcp.server.mcpserver`) and v1 `FastMCP` (`mcp.server.fastmcp`).
- No secrets are read or written here. Keys belong in `.env` (gitignored).
