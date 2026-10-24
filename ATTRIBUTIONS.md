# Attributions

Fathom is MIT-licensed (see [LICENSE](LICENSE)). It builds on the data, research and open-source software below. Each item keeps its own license.

## Data

- **NOAA National Data Buoy Center (NDBC)**, realtime standard meteorological feed (stations 44013, 44029, 44098, 44090): https://www.ndbc.noaa.gov/. U.S. Government work, public domain. Used for wave height, wind and sea temperature in `data/snapshots/conditions.json`.
- **NOAA Fisheries**, North Atlantic right whale vessel-strike rules and Seasonal Management Areas: https://www.fisheries.noaa.gov/. Public domain. Zone shapes in `data/snapshots/zones.json` are hand-digitized approximations and are marked `synthetic: true` where no authoritative file was used.
- **BOEM** offshore wind lease areas (reference for the hand-drawn wind areas): https://www.boem.gov/. Public domain.
- Whale sightings, the land mask, the fishing-effort proxy and the fleet are **synthetic** demo data made by the team and are labelled as such in the app.

## Research

- Vanderlaan, A. S. M., and Taggart, C. T. (2007). *Vessel collisions with whales: the probability of lethal injury based on vessel speed.* Marine Mammal Science 23(1): 144–156. https://doi.org/10.1111/j.1748-7692.2006.00098.x. The shape of the speed-lethality curve in `config/risk.yaml` follows this paper.

## Basemap

- **CARTO** basemap tiles: © [CARTO](https://carto.com/attributions). Used under CARTO's free-tier terms with attribution.
- Map data © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors, available under the Open Database License (ODbL).

## Frontend libraries

| Package | License |
|---|---|
| [MapLibre GL JS](https://github.com/maplibre/maplibre-gl-js) (`maplibre-gl`) | BSD-3-Clause |
| [deck.gl](https://deck.gl) (`@deck.gl/core`, `@deck.gl/layers`, `@deck.gl/mapbox`) | MIT |
| React, React DOM | MIT |
| Vite, `@vitejs/plugin-react` | MIT |
| Tailwind CSS, `@tailwindcss/vite` | MIT |
| TypeScript | Apache-2.0 |
| `@types/react`, `@types/react-dom` | MIT |

## Backend libraries

| Package | License |
|---|---|
| FastAPI | MIT |
| Starlette | BSD-3-Clause |
| Uvicorn | BSD-3-Clause |
| Pydantic | MIT |
| PyYAML | MIT |
| NumPy | BSD-3-Clause (bundled parts: 0BSD, MIT, Zlib, CC0-1.0) |
| Shapely | BSD-3-Clause |
| HTTPX | BSD-3-Clause |
| GeoPandas | BSD-3-Clause |
| xarray | Apache-2.0 |
| pytest | MIT |
| [Hypothesis](https://hypothesis.works) | MPL-2.0 |
| Ruff (CI lint) | MIT |
| pip-audit (CI) | Apache-2.0 |
| MCP Python SDK (`mcp/`) | MIT |

Licenses were read from the installed package metadata. Transitive dependencies keep their own licenses; see `frontend/package-lock.json` and `pip-licenses` output for the full list.

## Tools

- Built with **Kiro** (spec-driven development). CI uses GitHub Actions and the gitleaks secret scanner (MIT).
