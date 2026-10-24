# Fathom MCP server (`fathom_mcp`)

Exposes Fathom's **eight data/risk/route tools** (see
`.kiro/specs/fathom/design.md`, section 7) over the
[Model Context Protocol](https://modelcontextprotocol.io) using the official
`mcp` Python SDK. The same server is used two ways:

- the **in-app LLM agent** calls it at runtime to get facts it must cite;
- **Kiro** calls it during development to query the same data while writing code.

> **Status: skeleton.** Every tool validates its input and returns clearly
> labelled **placeholder** data (`placeholder: true`). No tool computes real
> risk, routes, zones, or conditions yet — the deterministic engine (Lanes A/B)
> will back these later. Nothing here should be treated as real output.

## The eight tools

| Tool | Input | Returns (eventually) |
|---|---|---|
| `get_conditions` | bbox, time range | wave / wind / SST per cell + source |
| `get_zones` | bbox, time | zones active/inactive + source URLs |
| `get_whale_risk` | bbox, time, speed_kn | risk grid (0–1) + top factors per cell |
| `plan_routes` | TripRequest | 2–3 `RoutePlan` objects |
| `get_effort_proxy` | bbox, month | normalized historical effort grid |
| `estimate_fuel` | route, vessel | liters (clearly labelled estimate) |
| `simulate_zone` | polygon, fleet sample id | Δrisk, Δtime, Δeffort + per-vessel detail |
| `export_brief` | RoutePlan, language | one-page HTML/PDF path |

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
    tools.py              # the eight tool functions (validate -> placeholder)
    models.py             # pydantic input models (bbox, time range, per-tool args)
    placeholders.py       # placeholder-response envelope helpers
```

## Run

```bash
pip install -e .          # or: pip install -r requirements.txt
python -m fathom_mcp      # starts the stdio MCP server
```

The command `python -m fathom_mcp` is the entry point referenced by
`.kiro/settings/mcp.json`. The `fathom` server there is **disabled** on purpose
until the real engine is wired in; flip `disabled` to `false` when ready.

## Notes for reviewers (Lane D: Product / QA / Story)

- Input validation uses pydantic v2; invalid input yields a structured
  `{"error": "invalid_input", "detail": [...]}` result instead of crashing.
- The server module supports both SDK lines: v2 `MCPServer`
  (`mcp.server.mcpserver`) and v1 `FastMCP` (`mcp.server.fastmcp`).
- No secrets are read or written here. Keys belong in `.env` (gitignored).
