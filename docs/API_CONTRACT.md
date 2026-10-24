# Fathom API contract

Owner: Lane B. Item shapes follow `frontend/src/api/types.ts`; if the two disagree, the TypeScript types win and this file gets fixed.

- Base path: `/api`. All times are UTC ISO-8601. Units: knots (kn), meters (m), hours (h), liters (l).
- Every data response carries provenance: `source`, `fetched_at`, `cached`, `synthetic`. Layer endpoints return an envelope with a `provenance` block plus an `items` array whose elements are the frontend types. Each item also carries `cached` and `synthetic`.
- Anything not from a real source has `synthetic: true`.
- Errors use a generic body `{"error": "<short message>"}` with no stack traces. Status codes: `422` invalid input, `413` body over 1 MB, `429` rate limited (60 requests/min per IP), `504` request took longer than 20 s, `500` anything else.
- Advisory only. No endpoint states that a plan is legally compliant.

## GET /api/health

Liveness. Answers immediately, even during warm-up.

```json
{ "status": "ok" }
```

## GET /api/ready

Readiness. `503 {"status": "warming_up"}` (with `Retry-After: 5`) until the startup warm-up has loaded the snapshots, grid, risk surfaces and one demo plan, then `200 {"status": "ready", "warmup_seconds": 0.45}`.

## Headers, CORS and docs

- CORS: origins from `FATHOM_ALLOWED_ORIGINS` (comma-separated, trimmed, trailing `/` removed), methods GET/POST/OPTIONS, header `content-type`, no credentials. An OPTIONS request without `Access-Control-Request-Method` gets 204 (with Allow-Origin only for allowed origins) instead of 405.
- Every response: `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `X-Frame-Options: DENY`, `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'`. `Strict-Transport-Security` is sent on HTTPS requests behind the trusted proxy. `Cache-Control: no-store` is sent on every POST and every `/api/trip/*` response.
- `/docs`, `/redoc` and `/openapi.json` are off unless `FATHOM_ENABLE_DOCS=true`.

## GET /api/meta/sources

Returns `MetaResponse`.

```json
{
  "demo_mode": true,
  "data_timestamp": "2026-03-14T21:05:00Z",
  "sources": [
    {
      "layer": "conditions",
      "name": "noaa_ndbc_44013+nws",
      "source_url": "https://www.ndbc.noaa.gov/station_page.php?station=44013",
      "fetched_at": "2026-03-14T18:05:00Z",
      "cached": true,
      "synthetic": false
    },
    { "layer": "zones", "name": "zones.json", "source_url": null, "fetched_at": "2026-03-14T00:00:00Z", "cached": true, "synthetic": true },
    { "layer": "sightings", "name": "sightings.json", "source_url": null, "fetched_at": "2026-03-14T00:00:00Z", "cached": true, "synthetic": true },
    { "layer": "land_mask", "name": "land_mask.geojson", "source_url": null, "fetched_at": null, "cached": true, "synthetic": true }
  ]
}
```

`zones.synthetic` is true when at least one zone in the snapshot is synthetic.

## Layers

Common query parameters:

| Param | Type | Rule |
|---|---|---|
| `bbox` | `min_lon,min_lat,max_lon,max_lat` | optional; lon in [-180, 180], lat in [-90, 90], min <= max |
| `time` | ISO-8601 datetime | optional; defaults to the latest snapshot time |
| `speed` | float, knots | risk only; 0 < speed <= 40, default 10 |

### GET /api/layers/conditions?bbox&time

Items are `Conditions`. `bbox` is applied by mapping each `cell_id` to its grid cell centroid. `time` picks the 3-hour slice; if no record matches, the nearest earlier slice is used.

```json
{
  "layer": "conditions",
  "query": { "bbox": "-71,41,-69,43.5", "time": "2026-03-14T18:00:00Z" },
  "provenance": {
    "source": "noaa_ndbc_44013+nws",
    "source_url": "https://www.ndbc.noaa.gov/station_page.php?station=44013",
    "fetched_at": "2026-03-14T18:05:00Z",
    "cached": true,
    "synthetic": false,
    "demo_mode": true
  },
  "count": 1,
  "items": [
    {
      "cell_id": "8_19", "time": "2026-03-14T18:00:00Z",
      "wave_m": 1.4, "wind_kn": 12.5, "sst_c": 6.2,
      "source": "noaa_ndbc_44013", "fetched_at": "2026-03-14T18:05:00Z",
      "lon": -70.575, "lat": 41.975, "cached": true, "synthetic": false
    }
  ]
}
```

### GET /api/layers/zones?bbox&time

Items are `Zone` plus `active` (bool, at `time`) and `restriction` (plain text). Inactive zones are returned with `active: false` so the map can dim them. `bbox` keeps zones whose polygon intersects the box.

```json
{
  "layer": "zones",
  "query": { "bbox": null, "time": "2026-03-14T18:00:00Z" },
  "provenance": { "source": "zones.json", "source_url": null, "fetched_at": "2026-03-14T00:00:00Z", "cached": true, "synthetic": true, "demo_mode": true },
  "count": 5,
  "items": [
    {
      "id": "sma_cape_cod_bay", "name": "Cape Cod Bay Seasonal Management Area", "kind": "whale_sma",
      "geometry": { "type": "Polygon", "coordinates": [[[-70.65, 41.75], [-70.0, 41.75], [-70.0, 42.1], [-70.65, 42.1], [-70.65, 41.75]]] },
      "active_from": "2026-01-01T00:00:00Z", "active_to": "2026-05-15T00:00:00Z",
      "speed_limit_kn": 10.0, "prohibited": false,
      "source_url": "https://www.fisheries.noaa.gov/...", "source_updated": "2026-01-01T00:00:00Z",
      "synthetic": false, "active": true, "restriction": "Speed limit 10 kn while active.", "cached": true
    }
  ]
}
```

### GET /api/layers/risk?bbox&time&speed

Items are `RiskCell`, computed by `app/engine/risk.py` (Lane A) over water cells of the grid. Cells with risk below 0.001 are omitted. Risk parameters are marked TODO-VERIFY in `config/risk.yaml`, and the sightings are synthetic, so this layer is `synthetic: true`.

```json
{
  "layer": "risk",
  "query": { "bbox": null, "time": "2026-03-14T18:00:00Z", "speed_kn": 12.0 },
  "provenance": { "source": "app.engine.risk + sightings.json", "source_url": null, "fetched_at": "2026-03-14T00:00:00Z", "cached": true, "synthetic": true, "demo_mode": true },
  "count": 1,
  "items": [
    { "cell_id": "15_19", "lon": -70.225, "lat": 41.975, "risk": 0.4113,
      "factors": { "presence": 0.53, "recency": 0.81, "lethality": 0.52 }, "cached": true, "synthetic": true }
  ]
}
```

## POST /api/trip/plan

Body is `TripRequest`:

```json
{
  "port": "provincetown",
  "vessel": "mid_trawler",
  "cruise_kn": 9.5,
  "max_hours": 14,
  "depart_window": ["2026-03-15T09:00:00Z", "2026-03-15T09:00:00Z"],
  "target_ground": "stellwagen_bank",
  "risk_pref": 0.6,
  "language": "en"
}
```

Bounds: `cruise_kn` in (0, 30], `max_hours` in (0, 72], `risk_pref` in [0, 1]. Known ports and grounds come from `config/ports.yaml`: ports `gloucester`, `boston`, `plymouth`, `provincetown`, `new_bedford`; grounds `stellwagen_bank`, `jeffreys_ledge`, `cape_cod_bay`. `max_hours` is the round-trip budget. If `target_ground` is null, `stellwagen_bank` is used. Unknown names return `422`.

Response is `text/event-stream`. Each message is `event: <name>` plus one `data:` line of JSON. At most 8 tool calls.

| Event | `data` |
|---|---|
| `tool_call` | `AgentEvent` with `status: "running"`, plus `args` |
| `tool_result` | `AgentEvent` with `status: "done"` and a one-line `detail`, plus `result` (the tool output that citations point to) |
| `plans` | `{ "plans": RoutePlan[], "narrative": [{ "text": "...", "citations": ["call_4"] }], "language": "en", "disclaimer": "...", "message": null, "synthetic": true }`. Each plan also has `round_trip_hours`, `zones_avoided`, `slow_zone_hours`, `estimate: true`. |
| `done` | `{ "tool_calls": 6 }` |
| `error` | `{ "error": "short message" }` |

```
event: tool_call
data: {"id": "call_1", "tool": "get_conditions", "label": "Checking weather and sea state…", "status": "running", "args": {"bbox": [-70.6, 41.9, -70.1, 42.4]}}

event: tool_result
data: {"id": "call_1", "tool": "get_conditions", "label": "Checking weather and sea state…", "status": "done", "detail": "3 readings, max wave 2.1 m", "result": {...}}

event: plans
data: {"plans": [{"name": "Fastest", "waypoints": [[-70.19, 42.06], [-70.3, 42.35]], "eta_hours": 3.4, "fuel_est_l": 160.2, "zones_crossed": ["slow_zone_stellwagen_mar"], "max_wave_m": 1.6, "risk_exposure": 0.31, "effort_proxy": 0.7, "weather_window": {...}, "citations": [...]}], "narrative": [{"text": "Fastest: about 3.4 hours [tool:call_4].", "citations": ["call_4"]}], "language": "en", "disclaimer": "Advisory only...", "message": null}

event: done
data: {"tool_calls": 6}
```

If no legal route exists, `plans` is `[]` and `message` names the constraint to relax, for example `"No legal route within 2 h. Relax: max_hours (shortest legal route needs about 3.4 h)."`.

Every narrative sentence ends with `[tool:call_N]`. Numbers and zone names are identical in `en`, `pt`, and `es`. `effort_proxy` is an estimate, not catch or revenue.

### Plan fields added in the QA round

- `plans[]` are **sorted by `eta_hours` ascending**, so Fastest comes first and `rank` 1..n follows that order. `recommended: true` marks the single plan that best fits the requester's `risk_pref`. Names describe the measured numbers:
  - `Fastest`: least time.
  - `Safest`: the **minimum** whale-risk exposure among the returned plans, and only if that is below Fastest's. No other plan is ever called Safest.
  - `Balanced`: less risk than Fastest and less time than Safest (at most one plan).
  - `Alternative`, or `Alternative 1`, `Alternative 2` when there are several: a different track that is not better on either measure. Translated as `Alternativa` in Portuguese and Spanish.

  Each plan also carries `risk_weight` (0.1 / 0.5 / 0.9), `method` (`risk_weight`, or `corridor` when a cost on earlier tracks was needed to find a different one), `vs_fastest {extra_hours, risk_change}`, `max_wind_kn` and `origin_adjusted_nm` (how far the port was moved off a coastal land cell, at most 3 cells).
- `target_ground` may be a named ground or `"lon,lat"` inside the study area. The frontend's "plan to nearest open water" button sends `nearest_open` this way. Anything else returns 422 with `fields: ["target_ground"]`.
- Whale risk is cached per 30-minute time bucket (evaluated at the bucket middle), and the risk layer per (bucket, speed to 0.1 kn). Startup warm-up runs one plan per port and vessel for the replay date (2026-03-15T13:00Z) and for the current time, so plans are fast once `/api/ready` returns 200.
- Two tracks are duplicates when more than 90 % of each lies within one grid cell (0.05°) of the other. If only one distinct track exists, `single_route_reason` explains why and the narrative says "All weightings give the same route because ...".
- `waypoints` are dense: the cell-centre track simplified only to a 0.5-cell tolerance, and never across land.
- All displayed numbers use one rounding helper (`app.engine.routing.rnd`): m and kn to 1 decimal, hours to 2, liters to 1, risk to 3, exposure to 4. The narrative's per-plan wave and wind values are the plan card's values.

### `access_lost` (shared with Lane D's simulator)

The router never moves a destination. If the target ground (or the departure port) is on land, outside the study area, or inside an **active closed (prohibited) zone**, including candidate zones passed as `extra_zones`, `route_one` and `plan_routes` return `ok: false`, `plans: []` and:

```json
"access_lost": {
  "endpoint": "destination",
  "code": "closed_zone",
  "reason": "is inside active closed zone Western Gulf of Maine Seasonal Closure",
  "zone_id": "closure_western_gom",
  "zone_name": "Western Gulf of Maine Seasonal Closure",
  "zone_active_to": "2026-04-30T00:00:00Z",
  "nearest_open": { "lon": -70.325, "lat": 42.925, "distance_nm": 3.6 }
}
```

`endpoint` is `destination` or `origin`. `code` is one of `closed_zone`, `land`, `outside` or `no_water`. `nearest_open` is the closest cell that is neither land nor closed, and it may be null. The SSE `plans` event repeats it as `access_lost`, and `message` gives the plain-language version. The simulator counts such trips as lost access (`access_lost_trips`) instead of as shorter trips.

**Baseline access loss is expected.** On the simulator's baseline date (2026-03-15), 57 of the 200 synthetic fleet trips report `access_lost`. Every one of them is a trip to Jeffreys Ledge (-70.25, 42.90). That point lies inside the Western Gulf of Maine Seasonal Closure (`closure_western_gom`, prohibited, active 2026-02-01 to 2026-04-30). None of the trips fail because of a land cell: all three fishing grounds sit in water cells. This is the correct result for the closure window, not a bug; outside the window the same trips route normally. `backend/tests/test_latency_order.py::test_baseline_access_lost_is_only_closed_jeffreys_ledge` checks this. Note for Lane D: the baseline explanation text in `engine/simulator.py` also names the Vineyard Wind construction exclusion, but no fleet ground is inside it, so that part of the sentence can be dropped.

### Validation (422)

`depart_window` must satisfy `start <= end` (equal is allowed; the frontend sends a single time twice), `end - start <= 14 days`, and a start no more than 7 days in the past. In demo mode the 7 days count back from the bundled data date (2026-03-14), so the March demo trips stay valid. Errors look like `{"error": "Invalid input.", "fields": ["depart_window"]}`. Unparseable JSON gives `"fields": ["body"]`.

## POST /api/trip/brief

Body:

```json
{ "plan": { "...": "RoutePlan" }, "language": "pt", "trip": { "...": "TripRequest (optional)" } }
```

Returns `text/html`: a one-page printable brief with waypoints, zone alerts, the weather window, data timestamps, and the advisory disclaimer.

## GET /api/sim/scenarios (Lane D, `backend/app/api/sim.py`)

```json
{
  "count": 3,
  "scenarios": [
    { "id": "extend_closure_east", "name": "Extend whale closure east", "description": "Extend the Western Gulf of Maine closure ~20 nm east (full no-entry)." },
    { "id": "dynamic_zone_sightings", "name": "Dynamic zone around recent sightings", "description": "..." },
    { "id": "seasonal_speed_limit", "name": "Seasonal 10-knot speed limit (instead of closure)", "description": "..." }
  ]
}
```

## POST /api/sim/run (Lane D)

Body: either `{ "scenario_id": "seasonal_speed_limit" }` (runs all preloaded options so the frontier is meaningful) or a custom polygon `{ "polygon": {"type": "Polygon", "coordinates": [...]}, "prohibited": true, "speed_limit_kn": null }`.

Response (fleet of 200 synthetic trips, routed by `app.engine.routing.route_one`):

```json
{
  "baseline": { "risk_exposure": 73.93, "steaming_hours": 928.08, "fuel_l": 53723.3, "effort_access": 45.76, "trips": 200 },
  "options": [
    {
      "scenario_id": "extend_closure_east",
      "name": "Extend whale closure east",
      "description": "...",
      "totals": { "risk_exposure": 74.63, "steaming_hours": 923.75, "fuel_l": 53557.6, "effort_access": 45.78, "trips": 200 },
      "deltas_pct": { "risk": 1.0, "hours": -0.5, "fuel": -0.3, "effort_access": 0.0 },
      "on_frontier": false,
      "summary": { "en": "...", "pt": "...", "es": "..." }
    }
  ],
  "fleet": "...", "router": "...", "labels": "...", "requested": "seasonal_speed_limit"
}
```

The frontend `ScenarioResult` maps `deltas_pct.risk` -> `delta_risk_pct`, and so on. A cold run takes about 9 to 12 s; repeat runs come from the route cache.
