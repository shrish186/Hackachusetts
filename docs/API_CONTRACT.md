# Fathom API contract

Owner: Lane B. Item shapes follow `frontend/src/api/types.ts`; if the two disagree, the TypeScript types win and this file gets fixed.

- Base path: `/api`. All times are UTC ISO-8601. Units: knots (kn), meters (m), hours (h), liters (l).
- Every data response carries provenance: `source`, `fetched_at`, `cached`, `synthetic`. Layer endpoints return an envelope with a `provenance` block plus an `items` array whose elements are the frontend types. Each item also carries `cached` and `synthetic`.
- Anything not from a real source has `synthetic: true`.
- Errors use a generic body `{"error": "<short message>"}` with no stack traces. Status codes: `422` invalid input, `413` body over 1 MB, `429` rate limited (60 requests/min per IP), `504` request took longer than 20 s, `500` anything else.
- Advisory only. No endpoint states that a plan is legally compliant.

## GET /api/health

```json
{ "status": "ok" }
```

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

Bounds: `cruise_kn` in (0, 30], `max_hours` in (0, 72], `risk_pref` in [0, 1]. Known ports: `gloucester`, `boston`, `plymouth`, `provincetown`, `new_bedford`, `chatham`. Known grounds: `stellwagen_bank`, `jeffreys_ledge`, `tillies_bank`, `cape_cod_bay`, `great_south_channel`. If `target_ground` is null, `stellwagen_bank` is used. Unknown names return `422`.

Response is `text/event-stream`. Each message is `event: <name>` plus one `data:` line of JSON. At most 8 tool calls.

| Event | `data` |
|---|---|
| `tool_call` | `AgentEvent` with `status: "running"`, plus `args` |
| `tool_result` | `AgentEvent` with `status: "done"` and a one-line `detail`, plus `result` (the tool output that citations point to) |
| `plans` | `{ "plans": RoutePlan[], "narrative": [{ "text": "...", "citations": ["call_4"] }], "language": "en", "disclaimer": "...", "message": null }` |
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

## POST /api/trip/brief

Body:

```json
{ "plan": { "...": "RoutePlan" }, "language": "pt", "trip": { "...": "TripRequest (optional)" } }
```

Returns `text/html`: a one-page printable brief with waypoints, zone alerts, the weather window, data timestamps, and the advisory disclaimer.

## GET /api/sim/scenarios (Lane D, `backend/app/api/sim.py`)

```json
[
  { "scenario_id": "full_closure", "label": "Full closure of Stellwagen approach", "synthetic": true },
  { "scenario_id": "dynamic_zone", "label": "Dynamic zone around latest sightings", "synthetic": true },
  { "scenario_id": "seasonal_speed_limit", "label": "Seasonal 10 kn speed limit (no closure)", "synthetic": true }
]
```

## POST /api/sim/run (Lane D)

Body: `{ "scenario_ids": ["full_closure", "dynamic_zone"] }` (omit to run all). Returns `ScenarioResult[]`:

```json
[
  {
    "scenario_id": "dynamic_zone",
    "label": "Dynamic zone around latest sightings",
    "delta_risk_pct": -54.0,
    "delta_hours_pct": 5.1,
    "delta_fuel_pct": 5.6,
    "delta_effort_access_pct": -9.0,
    "on_frontier": true,
    "summary": "Plain-language summary for a board member."
  }
]
```

The simulator can call `app.engine.routing.route_one(..., extra_zones=[Zone])` to re-route each trip around a candidate zone.
