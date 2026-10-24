# Fathom — Frontend (Lane C)

Map-first web app for Fathom, the advisory ocean decision copilot. Two modes:

- **Captain** — trip planner (request panel + ranked plan cards).
- **Manager** — policy what-if simulator (scenario trade-offs).

See the spec in `.kiro/specs/fathom/` (requirements, design §10, tasks). This
lane only owns `/frontend`.

## Stack

React + Vite + TypeScript, Tailwind CSS v4, MapLibre GL, deck.gl.

- **Basemap:** CARTO dark raster tiles — free, **no API key** required
  (attribution included). Defined in `src/map/basemap.ts`.
- **Theme:** dark ocean (`src/index.css` `@theme` tokens).

## Run

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173
npm run build    # type-check + production build
```

## Mock-first

The app runs **entirely on mock data** until the real backend exists, so the
map, mode toggle, time slider, zones, risk heatmap, routes, and scenarios all
work with no server.

- Mock fixtures: `src/mocks/*.json` — shapes match the API in
  `design.md §9` and the examples in `/data/snapshots/examples`.
- The conditions and risk **grids** are generated deterministically over the
  study bbox in `src/mocks/index.ts`.
- The API client (`src/api/client.ts`) reads `VITE_USE_MOCKS`
  (default `true`). Set it to `false` with the FastAPI backend running behind
  the `/api` proxy (see `vite.config.ts`) to use real endpoints.

## Layout

```
src/
  api/         types + client (mock ↔ real switch)
  mocks/       fake JSON fixtures + grid generators
  config/      study-area bbox / grid resolution
  map/         MapLibre view, basemap style, deck.gl layers
  state/       app state (mode, time slice, speed, layer toggles)
  hooks/       data-loading hooks
  lib/         time + zone helpers
  components/  TopBar, ModeToggle, DemoBadge, TimeSlider, LayerPanel, popups
  captain/     Captain mode panel
  manager/     Manager mode panel
```

## Safety / honesty (per steering)

- A **"Demo data"** badge shows whenever the app is on bundled data.
- Synthetic and cached data are labeled on screen.
- Advisory disclaimer is always visible; the UI never claims legal compliance.
- No secrets in the repo — see `.env.example` for variable names only.
