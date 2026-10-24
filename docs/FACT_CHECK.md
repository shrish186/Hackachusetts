# Fact check — Fathom

Every fact from the "Facts to verify" list in `docs/pitch.md`, checked against a
source URL. Honest status: **VERIFIED** (confirmed against an authoritative
source this session) or **NOT VERIFIED** (could not confirm within the time box
— do not put on a slide as fact).

Last checked: 2026-10-24 (UTC).

---

## 1. North Atlantic right whale population — **VERIFIED**

- **Finding:** ~**384** whales at the start of 2024 (95% credible interval
  375–394), per the North Atlantic Right Whale Consortium / New England
  Aquarium estimate released 2025-10-21, using NOAA capture-recapture data.
- **Sources:**
  - NOAA Library — Population size estimation 1990–2024:
    https://repository.library.noaa.gov/view/noaa/72014
  - IWC status summary (384, 375–394, 2024):
    https://iwc.int/about-whales/intro-to-population-status/status-of-whales-graphics/status-summary-na-right-whale
  - New England Aquarium / WDC announcement (384 alive during 2024, up from
    ~370 in 2023): https://us.whales.org/2025/10/21/north-atlantic-right-whale-population-shows-recovery/
- **Note:** Older NOAA UME fact sheets say "approximately 360–380"; use the 2024
  consortium figure (~384) and cite the year.

## 2. Vanderlaan & Taggart (2007) lethality numbers — **VERIFIED**

- **Finding:** Probability of a lethal injury to a large whale reaches **0.5 at
  11.8 knots**; rises from 0.21 at 8.6 kn to 0.79 at 15 kn; asymptotes to ~1
  above ~21 kn.
- **Source (open PDF):**
  http://www.phys.ocean.dal.ca/~taggart/Publications/Vanderlaan_Taggart_MarMamSci-23_2007.pdf
  (Marine Mammal Science 23(1):144–156, 2007.)
- **Applied in `config/risk.yaml`:** v50_kn = 11.8 (verified); k = 2.415
  (derived from the two published anchor points; fits 0.81 at 15.3 kn and ~0.98
  at 21 kn).

## 3. Seasonal Management Area dates and speed limits — **DATES VERIFIED; polygons approximate**

- **Dates/limits VERIFIED against NOAA Fisheries (2026 season bulletins):**
  - Cape Cod Bay SMA: active **Jan 1 – May 15**, 10 kn for vessels ≥ 65 ft.
    https://content.govdelivery.com/accounts/USNOAAFISHERIES/bulletins/401441e
  - Off Race Point SMA: active **Mar 1 – Apr 30**, 10 kn for vessels ≥ 65 ft.
  - Great South Channel SMA: active **Apr 1 – Jul 31**, 10 kn for vessels ≥ 65 ft.
    https://content.govdelivery.com/accounts/USNOAAFISHERIES/bulletins/40ff22f
  - General rule: https://www.fisheries.noaa.gov/new-england-mid-atlantic/endangered-species-conservation/reducing-vessel-strikes-north-atlantic-right-whales
- **Still approximate:** the zone **polygons** in `data/snapshots/zones.json`
  are hand-drawn approximations of the official areas, not the NOAA shapefiles,
  so every zone keeps `synthetic: true` with a per-zone `note` saying so.
- **Honesty note on the live API:** on a date outside these windows (e.g.
  24 Oct) the SMAs correctly report **inactive** — that is correct, not a bug.
  Use the `config/demo_scenarios.yaml` "Replay whale season" date (2026-03-15)
  to see them active.
- **Important:** the 10 kn limit is mandatory only for vessels ≥ 65 ft; Fathom
  treats it as advisory for all vessels and never claims legal compliance.

## 4. Wind lease area names and boundaries — **NOT VERIFIED**

- `zones.json` references "Vineyard Wind Lease Area (OCS-A 0501)" and a
  construction exclusion, but the **polygons are hand-drawn boxes, not the BOEM
  GeoJSON**, and the lease ID / name were not confirmed against BOEM this
  session. Marked `synthetic: true`.
- To verify: BOEM renewable-energy Massachusetts activities and the BOEM lease
  area GIS downloads.

---

## 5. Whale sightings — **REAL (OBIS)** as of 2026-10-24

- `data/snapshots/sightings.json` now holds **real** North Atlantic right whale
  (*Eubalaena glacialis*) occurrence records pulled from OBIS for the study
  bbox (NOAA/NMFS/NEFSC surveys aggregated by OBIS; CC-BY). The demo retains the
  60 most-recent records for routing performance. `synthetic: false`.
- Source: https://obis.org/  (API https://api.obis.org/)

## 6. Ocean conditions — **REAL (NOAA NDBC + NWS)** as of 2026-10-24

- `data/snapshots/conditions.json` holds **real** NOAA NDBC buoy observations
  (44013 Boston, 44029 Mass Bay) plus **real** NWS marine gridpoint forecast
  samples (api.weather.gov) for study-wide wave/wind coverage. `synthetic: false`.

---

## Summary for the judges

- **Real data:** ocean conditions (NOAA NDBC buoys + NWS forecast), whale
  sightings (OBIS), and the verified lethality-curve parameters.
- **Verified facts (safe to state):** right whale population (~384, 2024); the
  speed–lethality curve (0.5 at 11.8 kn); SMA active **dates** and the 10 kn
  limit for vessels ≥ 65 ft.
- **Still demo/synthetic (labeled):** zone **polygons** (hand-drawn
  approximations of real NOAA/BOEM areas — dates are real, shapes are not), the
  coastline/land mask, the effort proxy, and the fleet. The whale-risk layer is
  a transparent screening **model** over real inputs, not a measured value.
