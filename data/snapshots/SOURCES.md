# Data sources — Fathom snapshots

Honest status of every data layer. "Real" = downloaded from a real URL this
session with `synthetic: false`. "Synthetic" = hand-authored / seeded and
labeled `synthetic: true`. Times are UTC.

| Layer | File | Status | Source URL | fetched_at (UTC) | Notes |
|---|---|---|---|---|---|
| Conditions (buoy obs) | `conditions.json` | **REAL (live)** | https://www.ndbc.noaa.gov/data/realtime2/ | 2026-10-24 ~16:55Z | NOAA NDBC standard-met feed, buoys 44013 (Boston) + 44029 (Mass Bay). Only rows with BOTH real wave + wind kept. 44090/44098 had no complete row and were skipped. |
| Marine forecast (NWS) | — | **NOT DONE** | https://api.weather.gov | — | Skipped under time box; conditions covered by NDBC buoys instead. |
| Protection zones | `zones.json` | **SYNTHETIC** | NOAA Fisheries / Mass DMF / BOEM pages referenced per-zone | 2026-03-14 (demo date) | Polygons are hand-digitized from published maps; dates/limits are demo values. Each zone `synthetic: true`. NOT a real geospatial download. |
| Wind lease areas | `zones.json` (`wind_lease_*`) | **SYNTHETIC** | https://www.boem.gov/renewable-energy/state-activities/massachusetts | — | Hand-drawn boxes, not the real BOEM GeoJSON. |
| Coastline / land mask | `land_mask.geojson` | **SYNTHETIC** | (none) | — | Simplified hand-digitized MA coastline. Not Natural Earth / NOAA shoreline. Coarse: some real ports fall on "land" cells. |
| Whale sightings | `sightings.json` | **SYNTHETIC** | (none) | 2026-03-14 (demo date) | Seeded from published seasonal patterns; aggregate, no individual identity. Not an OBIS download. |
| Effort proxy | (computed) `engine/effort.py` | **SYNTHETIC** | (none) | — | Gaussian field around known grounds. An ESTIMATE, not catch/revenue. |
| Fleet | (computed) `engine/fleet.py` | **SYNTHETIC** | (none) | — | Deterministic anonymous trips (V-001..), seeded from real port/ground coords. |
| Ports & grounds | `config/ports.yaml` | REAL coordinates | public gazetteer / NOAA charts | — | Point locations are real; everything built on them is still a model estimate. |
| Lethality curve | `config/risk.yaml` | **REAL (verified)** | http://www.phys.ocean.dal.ca/~taggart/Publications/Vanderlaan_Taggart_MarMamSci-23_2007.pdf | 2026-10-24 | v50=11.8 kn verified; k=2.415 derived from published anchor points. |

## What is real vs. synthetic (one line)
Real: NDBC buoy conditions (2 stations), the lethality curve parameters, and
port/ground coordinates. Everything else (zones, coastline, sightings, effort,
fleet) is synthetic and labeled as such.

## How to refresh the real buoy data
`python -c "from app.ingest.ndbc import fetch_all; print(fetch_all())"` (run
from `backend/` with `FATHOM_ROOT` set), then regenerate `conditions.json`.
