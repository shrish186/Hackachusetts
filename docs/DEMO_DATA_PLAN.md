# Fathom — Demo Data Plan

**Owner:** Lane D (Product / QA / Story) · **Status:** draft for Hour-0 reality check

## The one scenario we demo

- **Departure port:** **Gloucester, MA** (Captain Joe's home port).
- **Date / time:** **Saturday, 15 March 2025, 06:00 America/New_York** (11:00 UTC).
- **Why this date:** mid-March is peak North Atlantic right whale season in Cape
  Cod and Massachusetts Bays, so the whale-risk layer and the slow zones are
  both *active* — the whole point of the demo. On this date two real
  restrictions overlap and bite:
  - **Cape Cod Bay Seasonal Management Area (SMA)** — NOAA, 10 kn for vessels
    ≥ 65 ft, active ~Jan 1 onward. [NOAA Fisheries](https://www.fisheries.noaa.gov/)
  - **Cape Cod Bay Restricted Speed Area** — MA DMF small-vessel (< 65 ft) 10 kn
    limit, **March 1 – April 30**. [MA DMF, 322 CMR 12.05](https://www.mass.gov/news/massachusetts-waters-seasonal-right-whale-habitat)

A Gloucester captain heading to Stellwagen Bank or Jeffreys Ledge must plan
around an active slow zone and elevated whale risk — exactly what the planner is for.

> Everything below is a *candidate*; confirm each endpoint at Hour 0 and snapshot
> it immediately. If a source can't be fetched, fall back to the **synthetic**
> seed and label it on screen (steering: `data-and-safety.md`).

## Snapshot files we need (bundle in `/data/snapshots/`, small + committed)

| # | File | Layer | Source | Real or synthetic for demo |
|---|------|-------|--------|----------------------------|
| 1 | `conditions/buoys_2025-03-15.json` | Waves/wind/SST at buoys (e.g. NDBC 44013 Boston, 44018 Cape Cod) | NOAA NDBC | **Real** (snapshot the day's text feed) |
| 2 | `conditions/marine_forecast_2025-03-15.json` | Gridded marine forecast | NWS api.weather.gov | **Real** snapshot; **synthetic** fallback |
| 3 | `conditions/sst_2025-03-15.nc` (subset) | Sea-surface temp / chlorophyll | NOAA ERDDAP CoastWatch | **Real** subset; **synthetic** fallback |
| 4 | `zones/whale_smas.geojson` | Cape Cod Bay SMA polygon + dates | NOAA Fisheries | **Real** (or hand-digitized from published map) |
| 5 | `zones/dmf_restricted_speed_area.geojson` | MA DMF small-vessel speed area | MA DMF | **Real** / hand-digitized |
| 6 | `zones/fishing_closures.geojson` | Seasonal closures active mid-March | NOAA GARFO / MA DMF | **Real** / hand-digitized |
| 7 | `zones/wind_lease.geojson` | BOEM lease areas (context only) | BOEM | **Real** |
| 8 | `sightings/right_whale_2025-03.json` | Right whale sightings, March 2025 | OBIS / public sightings | **Real** sample; **synthetic** seed if sparse |
| 9 | `fleet/gloucester_fleet_sample.json` | ~200 vessel trips for the simulator | Derived from historical AIS | **Synthetic** (anonymized IDs) |
| 10 | `grid/land_mask.geojson` | Study-area land mask | Natural Earth / NOAA shoreline | **Real** (bundled) |

## Expected to be synthetic (label clearly on screen)

- **Fleet sample (#9):** seeded from Gloucester + known grounds; vessel identities
  are anonymized — never show a real vessel's identity (steering rule).
- **Effort proxy** derived from #9: it is an *estimate of activity, not catch or
  revenue* — badge it as such everywhere.
- **Any zone without a `source_url`:** hand-digitized from a published map →
  `synthetic: true` so the UI badges it.
- **Any live source that fails the Hour-0 check:** use the synthetic seed and say
  so in the pitch. Do not pretend.

## Acceptance checks before the demo

- [ ] App runs end-to-end with `FATHOM_DEMO_MODE=true` and **no network** (req. 10).
- [ ] Every layer shows a data timestamp; cached/synthetic layers show a badge.
- [ ] Planner returns 2–3 routes from Gloucester that respect the active slow zone
      (speed capped to 10 kn inside it) and avoid any prohibited/closed zone.
- [ ] Numbers and zone names are identical across EN / PT / ES briefs.
