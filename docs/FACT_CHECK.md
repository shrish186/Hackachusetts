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

## 3. Seasonal Management Area / slow-zone dates and speed limits — **NOT VERIFIED**

- The 10-knot speed limit is the well-known NOAA SMA figure, but the **exact
  active dates and polygon boundaries in `data/snapshots/zones.json` are
  hand-digitized demo values, not downloaded** from NOAA Fisheries. The Cape Cod
  Bay restricted-area dates (Mass DMF) were not confirmed this session.
- **Do not present specific SMA dates as fact.** To verify: NOAA Fisheries
  "Reducing Vessel Strikes to North Atlantic Right Whales" and the Mass DMF
  Cape Cod Bay regulations pages.
- Status in data: all such zones carry `synthetic: true`.

## 4. Wind lease area names and boundaries — **NOT VERIFIED**

- `zones.json` references "Vineyard Wind Lease Area (OCS-A 0501)" and a
  construction exclusion, but the **polygons are hand-drawn boxes, not the BOEM
  GeoJSON**, and the lease ID / name were not confirmed against BOEM this
  session. Marked `synthetic: true`.
- To verify: BOEM renewable-energy Massachusetts activities and the BOEM lease
  area GIS downloads.

---

## Summary for the judges

- **Safe to state as fact:** right whale population (~384, 2024) and the
  speed–lethality curve (0.5 at 11.8 kn), both cited above.
- **Must be labeled demo/synthetic:** all zone polygons and dates, wind lease
  names/boundaries, the coastline, whale sightings, effort proxy, and the fleet.
