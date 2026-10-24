# Data sources — Fathom snapshots

Honest status of every data layer, last refreshed **2026-10-24 (UTC)**.
"Real" = fetched from a real public URL this session (`synthetic: false`).
"Synthetic" = hand-authored / seeded / a derived model (`synthetic: true`).
See `docs/DATA.md` for the fuller table and `docs/FACT_CHECK.md` for verified facts.

| Layer | File | Source | URL | fetched_at | Status | License | Limitations |
|---|---|---|---|---|---|---|---|
| Conditions | `conditions.json` | NOAA NDBC buoys + NWS marine forecast | https://www.ndbc.noaa.gov/data/realtime2/ , https://api.weather.gov/ | 2026-10-24 | **REAL** | US Gov public domain | Buoys 44013/44029 only report a few cells; NWS gridpoint samples fill coverage. NWS rows are forecast, not observations. |
| Sightings | `sightings.json` | OBIS (NOAA/NMFS/NEFSC surveys) | https://obis.org/ | 2026-10-24 | **REAL** | CC-BY 4.0 | 60 most-recent **Jan-May (whale-season)** of thousands of in-bbox records, for routing speed. Historical seasonal records (2023-2025), not live detections; they drive the risk layer's seasonal presence term on a March replay. |
| Risk | (model) `app/engine/risk.py` + `config/risk.yaml` | Real OBIS sightings + Vanderlaan & Taggart (2007) lethality curve | http://www.phys.ocean.dal.ca/~taggart/Publications/Vanderlaan_Taggart_MarMamSci-23_2007.pdf | 2026-10-24 | **Model over real inputs** (flagged synthetic) | paper © authors; our code MIT | Screening model, not a measured probability. Params verified (v50=11.8 kn, k=2.415). |
| Zones | `zones.json` | NOAA Fisheries SMAs, GARFO/Mass DMF closures, BOEM wind leases | https://www.fisheries.noaa.gov/.../reducing-vessel-strikes-north-atlantic-right-whales | 2026-10-24 | **Dates real, polygons synthetic** | facts US Gov public domain | Polygons are hand-drawn approximations of the official areas. SMA active dates + 10 kn (≥65 ft) are verified. |
| Land mask | `land_mask.geojson` | Hand-drawn approximation of NOAA/Natural Earth coastline | https://www.naturalearthdata.com/downloads/10m-physical-vectors/10m-land/ | n/a | **Synthetic** | Natural Earth public domain; shapes ours | Coarse; ports snapped to nearest water cell. Not for navigation. |
| Ports & grounds | `config/ports.yaml` | Real harbor/ground coordinates | public gazetteer / NOAA charts | n/a | **Real coords** | — | 3 ports snapped to the nearest water cell (coarse land mask); all grounds in water. `jeffreys_ledge` is legitimately inside the Western GoM closure in whale season. Routes/effort built on these are estimates. |
| Effort proxy | (model) `app/engine/effort.py` | Seeded from `config/ports.yaml` grounds | — | n/a | **Synthetic** | our code MIT | An ESTIMATE of fishing activity, not catch or revenue. |
| Fleet | (model) `app/engine/fleet.py` | Deterministic synthetic, seeded from ports/grounds | — | n/a | **Synthetic** | our code MIT | Anonymous trips (V-001…); no real vessel identity. |

## Refresh
`python scripts/refresh_snapshots.py --all` re-fetches conditions (NDBC+NWS) and
sightings (OBIS) and rewrites the snapshots with a fresh `fetched_at`. If a
source is unreachable it keeps the previous snapshot and says so. Validate with
`python scripts/validate_snapshots.py`.
