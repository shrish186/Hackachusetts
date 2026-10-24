# Security findings (Lane D review)

Review of `backend/app` and `frontend/src` on 2026-10-24. Findings in **other
lanes** are written here for the owning lane to fix (I fixed issues in my own
lane directly: `mcp/`, `backend/app/engine/simulator.py`, `backend/app/api/sim.py`).

Severity: **High** = fix before submission if exposed publicly; **Medium** =
should fix; **Low** = hardening / note.

## Open findings (other lanes)

### F1 — Permissive CORS method/credentials combo (Lane B) — Medium
`backend/app/main.py` sets `allow_methods=["*"]` and `allow_headers=["*"]` with
`allow_credentials=True`. Origins are correctly pinned to a fixed list (good),
so this is not currently exploitable, but `*` methods/headers with credentials is
needlessly broad. **Fix:** restrict `allow_methods` to the verbs actually used
(`GET`, `POST`) and drop `allow_credentials=True` unless cookies are needed (the
API is stateless and uses none). Add deployed origins explicitly; never use
`allow_origins=["*"]` together with credentials.

### F2 — Snapshot loader builds paths from a name argument (Lane B) — Low (latent)
`backend/app/api/_snapshots.py::load_snapshot(name)` builds
`SNAPSHOT_DIR / f"{name}.json"`. Today every caller passes a hardcoded literal
(`"conditions"`, `"zones"`, `"sightings"`), so there is **no** path-traversal
exposure. It becomes a traversal risk only if a future endpoint passes a
request-controlled value. **Fix (defensive):** validate `name` against an
allowlist / `^[a-z_]+$` and resolve+confirm the path stays under `SNAPSHOT_DIR`.

### F3 — External basemap tiles over the network (Lane C) — Low
`frontend/src/map/basemap.ts` loads CARTO raster tiles from `*.basemaps.cartocdn.com`.
Fine for a live demo, but **demo mode is supposed to run with the network off**
(Req 10.1). **Fix/note:** document that the basemap needs network, or bundle a
minimal offline style for the no-network demo path. Links already use
`rel="noreferrer"` (good).

## Checked and clean

- **No `dangerouslySetInnerHTML`, `innerHTML`, or `eval`** anywhere in
  `frontend/src` — the trip brief is not rendered as raw HTML today. When
  `export_brief` is implemented, escape all interpolated values.
- **No secrets in code** — grep for api_key/secret/token/password/AKIA in
  `backend/app` and `frontend/src` found only field names and docstrings.
- **API input validation** — `bbox` is strictly parsed (4 floats, min<=max, 422
  on error); `speed` constrained `> 0`.
- **Risk layer honesty** — the uncalibrated risk stub forces `synthetic: true`
  on its provenance, so it cannot be mistaken for calibrated data.

## Fixed in my lane

- `backend/app/api/sim.py` validates the scenario id against an allowlist and
  validates any candidate polygon (type `Polygon`, closed ring, coords in range)
  before use; it never builds a filesystem path from request input.
- `mcp/fathom_mcp` exposes only the fixed tool allowlist; tool input is
  validated and errors are returned as structured data, never raised through the
  transport.
