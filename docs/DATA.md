# Fathom data layer (Lane A)

How every data layer is sourced, how fresh it is, and what is real vs. synthetic.
This is the human-readable companion to `data/snapshots/SOURCES.md` and the
machine checks in `scripts/validate_snapshots.py`.

Last refreshed: **2026-10-24 (UTC)**. All times UTC unless a local label is given.

## Source table

| Layer | Source | URL | fetched_at | Real / synthetic | Limitations | License |
|---|---|---|---|---|---|---|
| Conditions (wave, wind, SST) | NOAA NDBC buoys + NWS marine gridpoint forecast | ndbc.noaa.gov/data/realtime2 ; api.weather.gov | 2026-10-24 | **Real** | 2 buoy cells + 5 NWS forecast samples; NWS rows are forecast | US Gov public domain |
| Whale sightings | OBIS (NOAA/NMFS/NEFSC surveys) | obis.org | 2026-10-24 | **Real** | 60 most-recent **Jan-May (whale-season)** in-bbox records, kept for routing speed | CC-BY 4.0 |
| Ports | real harbors, snapped to nearest water cell | NOAA charts / gazetteer | n/a | **Real coords (grid-snapped)** | 3 ports' harbor-mouth points landed in coarse land cells; moved to the adjacent water cell (within a few km) | — |
| Fishing grounds | real grounds | NOAA charts | n/a | **Real coords** | all in water; `jeffreys_ledge` is legitimately inside the Western GoM closure in whale season | — |
| Whale risk | model: real OBIS sightings × Vanderlaan & Taggart (2007) | doi.org/10.1111/j.1748-7692.2007.00048.x | 2026-10-24 | **Model over real inputs** (flagged synthetic) | screening model, not a probability of a real strike | paper © authors |
| Protection zones | NOAA SMAs, GARFO/Mass DMF closures, BOEM leases | fisheries.noaa.gov ; boem.gov | 2026-10-24 | **Dates real, polygons synthetic** | polygons are hand-drawn approximations | facts public domain |
| Land mask / coastline | hand-drawn approximation of NOAA/Natural Earth | naturalearthdata.com | n/a | **Synthetic** | coarse; ports snapped to water | Natural Earth public domain |
| Ports & grounds | real coordinates | NOAA charts / gazetteer | n/a | **Real coords** | derived routes/effort are estimates | — |
| Effort proxy | model seeded from grounds | — | n/a | **Synthetic** | an estimate, not catch/revenue | our code |
| Fleet | deterministic synthetic | — | n/a | **Synthetic** | anonymous trips, no real identity | our code |

## What became real this round

- **Conditions** → real NOAA NDBC buoy observations + real NWS marine forecast.
- **Sightings** → real OBIS North Atlantic right whale occurrences, now filtered
  to the **Jan-May whale season** so the March replay shows the genuine seasonal
  pattern (see "Whale-season replay" below).
- **SMA dates & 10 kn limit** → verified against NOAA 2026 season bulletins.

## Whale-season replay (15 Mar 2026) — why the heatmap is honest

The risk layer is `p_whale = alpha*presence + (1-alpha)*recency`, then times the
lethality curve. The bundled sightings are **real** OBIS records from past
whale seasons (2023-2025, Jan-May). On the 2026-03-15 replay their *recency*
term is ~0 (they are years old), so the March heatmap is driven by the
**seasonal presence** term — i.e. it shows where right whales really have been
in Massachusetts/Cape Cod Bay in spring, not fabricated recent detections. This
is deliberate and labeled: we never invent recent sightings to make the demo
look live. At the replay date the risk grid peaks around 0.31 at 12 kn with a few
hundred non-trivial cells, concentrated in Cape Cod Bay / Stellwagen — matching
the known spring aggregation.

## Fleet access at baseline — grounds, ports, and legitimate closures (task 3)

QA reported **57 of 200** simulated trips with `access_lost` at baseline. I
traced it:

- **Root cause = a legitimate closure, not a bug.** The 200-trip fleet (seed 42)
  assigns exactly **57 trips to `jeffreys_ledge`**, and Jeffreys Ledge sits
  inside the **Western Gulf of Maine seasonal closure**, which is active in
  whale season (including the 2026-03-15 replay date). Those 57 trips lose
  access *because the regulation closes that ground* — that is the simulator
  correctly showing the livelihood cost of the closure, not a data error. The
  ground is left unchanged. Out of season the closure is inactive and access
  returns. `access_lost` after the port fix below is still exactly 57, which
  confirms the cause is the closure and nothing else.
- **Ports on land (fixed anyway).** Separately, the coarse synthetic land mask
  put three real harbor-mouth points (Gloucester, Boston, Plymouth) inside
  "land" cells. `config/ports.yaml` now uses the nearest navigable **water**
  cell to each harbor (within a few km) so every trip origin is routable; all
  five ports and all three grounds now resolve to water (tests enforce this).
  This did not change baseline `access_lost` (the router already tolerated the
  origins), but it removes a latent correctness trap.
- **No fishing ground sits on land.**

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

## Relation to the hackathon datasets

> **Status: AWAITING the official list.** Anant has asked the team to paste the
> datasets Hackachusetts provides for the Climate Tech & Clean Energy track.
> Until that list is pasted here, this section is a **placeholder**: Fathom makes
> **no claim** of using any hackathon-provided dataset. Everything Fathom uses
> today is listed in the source table above and in `data/snapshots/SOURCES.md`
> (NOAA NDBC, NWS, OBIS, NOAA Fisheries, BOEM) and was fetched directly from
> those public sources — not from a hackathon bundle.

Once the official list is provided, fill one row per dataset. Use **Used** only
for datasets Fathom actually ingests; mark everything else **Not used** with a
one-line honest reason. Never mark a dataset "Used" that we did not ingest.

| Hackathon dataset | Provided for track | Used by Fathom? | Where / how (file, module) | Notes |
|---|---|---|---|---|
| _(awaiting list)_ | Climate Tech & Clean Energy | _(to fill)_ | _(to fill)_ | _(to fill)_ |

Honesty rule for this table: a row may say **Used** only if there is a concrete
ingest path (a `data/snapshots/*` file or a `backend/app/ingest/*` module that
reads it). If we evaluated a dataset but did not ingest it, say **Not used** and
why (e.g. "format/time not compatible", "superseded by the live NOAA feed").
