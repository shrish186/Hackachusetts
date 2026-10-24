# Security

Fathom is an **advisory** ocean decision copilot. It handles public and
synthetic data only and is built so that an LLM can never fabricate facts or act
outside a fixed set of tools. This document describes how we handle secrets,
what we validate, our limits, what we do not store, and how the agent is
constrained.

## Secrets handling

- **No secrets in the repo.** API keys and credentials live only in a local
  `.env`, which is gitignored (`.env`, `.env.*` are ignored; `.env.example`
  holds names only, never values).
- **CI enforces this.** `.github/workflows/ci.yml` runs **gitleaks** on every
  push and pull request to catch committed keys, tokens, and private keys.
- **Editor enforces this.** The `.kiro/hooks/secret-scan.kiro.hook` runs on every
  file save and flags API keys, bearer/access tokens, private keys, AWS keys
  (`AKIA...`), and raw `.env` content before it can be committed. The secret
  value is never echoed back.
- **Rotation.** If a secret is ever committed, treat it as compromised: remove
  it, rotate the key at the provider, and force-expire any derived tokens.

## Input validation

- **API parameters** are validated with pydantic v2 and FastAPI query
  constraints. The `bbox` query is parsed to exactly four floats with
  `min <= max` or rejected with HTTP 422. Speeds are constrained `> 0`.
- **Simulator input** (`POST /api/sim/run`) accepts either a known scenario id
  (checked against an allowlist) or a GeoJSON Polygon that is schema- and
  geometry-validated (type must be `Polygon`, ring closed, coordinates in
  range). Unknown ids and malformed polygons are rejected with 422.
- **Snapshot file access is not user-controlled.** Snapshot collection names are
  hardcoded constants in the endpoints, never taken from request input, so the
  loader cannot be steered to read arbitrary paths. New code MUST keep this
  property: never build a filesystem path from a request value.

## Rate limits and resource bounds

- The simulator caps work: the fleet sample is a fixed, bounded size (~200
  deterministic synthetic trips) and the baseline is **cached**, so a scenario
  run is one re-route pass with a hard target of **< 20 s**.
- The agent loop is capped at **8 tool calls per request** (design.md section 7)
  and the API targets a response or a clear error within **30 s**
  (requirements.md Req 10).
- Deploying publicly should add an edge/proxy rate limit (e.g. per-IP) in front
  of the API; the app itself exposes no unbounded or recursive endpoints.

## What the app does not store

- **No personal data** beyond a vessel type and a departure port
  (requirements.md Req 9.3). No names, no accounts, no contact details.
- **No real vessel identities.** The fleet sample used by the simulator is
  synthetic and anonymized; identities are never exposed (data-and-safety
  steering rule).
- **No tracking.** The app does not persist user locations or trip history
  server-side; a trip brief is generated on demand for the user to save locally.

## How the LLM agent is restricted

The agent orchestrates and explains; it never computes risk, routes, or zone
facts, and it cannot take arbitrary actions.

- **Tool allowlist.** The agent may only call the fixed set of Fathom tools
  (`get_conditions`, `get_zones`, `get_whale_risk`, `plan_routes`,
  `get_effort_proxy`, `estimate_fuel`, `simulate_zone`, `export_brief`). There is
  no shell, no file write, and no network tool. The `fathom` MCP server declares
  only these tools.
- **Tool output is treated as data, not instructions.** Results returned from
  tools are inserted as data for the model to summarize; the agent does not
  execute, follow, or trust instructions embedded in tool output or in fetched
  content.
- **Citation guard.** Every sentence containing a number, zone name, or date
  must carry a `[tool:call_id]` citation. Output is post-processed: an uncited
  factual claim is stripped or re-prompted once, and the event is logged
  (design.md section 7). If no tool supports a claim, the agent says it does not
  know rather than guessing.
- **No legal claims.** The agent never states that a plan is "legally
  compliant"; it only reports which known zones a plan avoids (Req 9.2), and
  every plan shows an advisory-only disclaimer (Req 9.1).

## Dependencies

- Python dependencies are audited in CI with **pip-audit**; Node dependencies
  with **npm audit --audit-level=high**. A high or critical advisory fails CI.

## Reporting

This is a hackathon project. For a real deployment, report suspected
vulnerabilities privately to the maintainers before public disclosure.
