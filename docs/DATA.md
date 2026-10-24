# Fathom data layer (Lane A)

How every data layer is sourced, how fresh it is, and what is real vs. synthetic.
This is the human-readable companion to `data/snapshots/SOURCES.md` and the
machine checks in `scripts/validate_snapshots.py`.

Last refreshed: **2026-10-24 (UTC)**. All times UTC unless a local label is given.

## Source table

| Layer | Source | URL | fetched_at | Real / synthetic | Limitations | License |
|---|---|---|---|---|---|---|
| Conditions (wave, wind, SST) | NOAA NDBC buoys + NWS marine gridpoint forecast | ndbc.noaa.gov/data/realtime2 ; api.weather.gov | 2026-10-24 | **Real** | 2 buoy cells + 5 NWS forecast samples; NWS rows are forecast | US Gov public domain |
| Whale sightings | OBIS (NOAA/NMFS/NEFSC surveys) | obis.org | 2026-10-24 | **Real** | 60 most-recent in-bbox records kept for routing speed | CC-BY 4.0 |
| Whale risk | model: real OBIS sightings × Vanderlaan & Taggart (2007) | doi.org/10.1111/j.1748-7692.2007.00048.x | 2026-10-24 | **Model over real inputs** (flagged synthetic) | screening model, not a probability of a real strike | paper © authors |
| Protection zones | NOAA SMAs, GARFO/Mass DMF closures, BOEM leases | fisheries.noaa.gov ; boem.gov | 2026-10-24 | **Dates real, polygons synthetic** | polygons are hand-drawn approximations | facts public domain |
| Land mask / coastline | hand-drawn approximation of NOAA/Natural Earth | naturalearthdata.com | n/a | **Synthetic** | coarse; ports snapped to water | Natural Earth public domain |
| Ports & grounds | real coordinates | NOAA charts / gazetteer | n/a | **Real coords** | derived routes/effort are estimates | — |
| Effort proxy | model seeded from grounds | — | n/a | **Synthetic** | an estimate, not catch/revenue | our code |
| Fleet | deterministic synthetic | — | n/a | **Synthetic** | anonymous trips, no real identity | our code |

## What became real this round

- **Conditions** → real NOAA NDBC buoy observations + real NWS marine forecast.
- **Sightings** → real OBIS North Atlantic right whale occurrences.
- **SMA dates & 10 kn limit** → verified against NOAA 2026 season bulletins.

## What is still synthetic (and honestly labeled)

- **Zone polygons** (hand-drawn approximations; the dates are real).
- **Land mask** (simplified coastline).
- **Effort proxy** and **fleet** (synthetic models).
- **Whale-risk layer** is a transparent screening model, not a measured value.

## Unreachable / deferred sources

- SST as a standalone gridded layer (GHRSST/ERDDAP) and bathymetry
  (GEBCO/ETOPO): deferred this round for time/stability. SST is currently
  carried per NDBC buoy reading (water temperature) where available.
- AIS-derived effort: no public AIS pulled; effort remains a synthetic proxy.
- When a source is unreachable, `scripts/refresh_snapshots.py` keeps the
  previous snapshot and prints a warning rather than writing dishonest data.

## Demo scenarios (`config/demo_scenarios.yaml`)

Seasonal Management Areas are only active in whale season, so a reviewer running
the live API in October correctly sees few/no active zones. To demo active
closures, use the bundled scenario:

- **`replay_whale_season`** — label **"Replay whale season"**
  - `time_utc`: `2026-03-15T13:00:00Z` (= 2026-03-15 09:00 EDT, America/New_York)
  - On this instant the Cape Cod Bay SMA, Off Race Point SMA, the example
    Stellwagen slow zone, and the western Gulf of Maine closure are all active.
- **`present_day`** — label **"Today (live)"**, `time_utc: null` (uses now).

### Frontend integration ("Replay whale season")

The zone/risk/conditions layer endpoints already accept a `time` query param
(UTC ISO-8601). To implement the **"Replay whale season"** button:

1. Read `config/demo_scenarios.yaml` → `scenarios.replay_whale_season.time_utc`
   (or hard-code `2026-03-15T13:00:00Z`).
2. Call the layer endpoints with `?time=2026-03-15T13:00:00Z` (and the usual
   `bbox`), e.g. `GET /api/layers/zones?time=2026-03-15T13:00:00Z`.
3. Set the time slider to that instant so conditions and risk match.

> NOTE for Lane B: please mirror this `time`-replay note in `docs/API_CONTRACT.md`
> (that file is Lane B-owned, so Lane A did not edit it). The layer endpoints
> already support the `time` param, so no API change is required.
