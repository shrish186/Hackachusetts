# Fathom — Frontend (Lane C)

Map-first web app for Fathom, the advisory ocean decision copilot. Two modes:

- **Captain** — trip planner (request panel + ranked plan cards).
- **Manager** — policy what-if simulator (scenario trade-offs).

See the spec in `.kiro/specs/fathom/` (requirements, design §10, tasks). This
lane only owns `/frontend`.

## Stack

React + Vite + TypeScript, Tailwind CSS v4, MapLibre GL, deck.gl.

- **Basemap:** OpenStreetMap raster tiles, darkened via MapLibre raster paint —
  free, **no API key** required (attribution included). Defined in
  `src/map/basemap.ts`. (CARTO's keyless tiles were discontinued in Aug 2026.)
- **Theme:** dark ocean (`src/index.css` `@theme` tokens).

## Run

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173
npm run build    # type-check + production build
```

## Backend connection & environment

The client talks to the real FastAPI backend and **gracefully degrades** to
bundled demo data when the backend is down.

| Env var | Default | Purpose |
|---|---|---|
| `VITE_API_URL` | `http://localhost:8000` | Base URL of the Fathom API. The client prefixes every request (`/api/...`) with this. |

Behavior (`src/api/client.ts`):

- Every request has a **4-second timeout**. If a request fails or times out,
  the client falls back to the bundled mock data in `src/mocks/` and flips a
  connection flag to **offline**.
- The badge in the top bar reflects this: **green "Live API"**, amber
  **"Demo data"** (API up but in demo mode), or red **"Offline demo data"**
  (API unreachable → in-browser mocks).
- The **risk heatmap and conditions** come from the API when it is up and only
  fall back to the in-browser generator when it is not.

To point at a deployed backend, set `VITE_API_URL` (e.g. in Vercel project env
or a local `.env.local` — see `.env.example`). **Never commit real `.env`
files.**

## Deployment (Vercel)

`vercel.json` at the repo root builds this app from the `frontend/`
subdirectory (`npm --prefix frontend run build`, output `frontend/dist`) and
adds:

- A **single-page-app rewrite** (`/(.*) → /index.html`) so client routes and
  reloads work.
- **Security headers:** `X-Content-Type-Options: nosniff`,
  `Referrer-Policy: strict-origin-when-cross-origin`, `X-Frame-Options: DENY`,
  and a **Content-Security-Policy**. The CSP allows the map tile host
  (`*.tile.openstreetmap.org`), `blob:` workers (MapLibre/deck.gl), inline
  styles, and `https:` API calls (so any `VITE_API_URL` origin works). Verified
  against a real `npm run build`: the app loads one external module script and
  one stylesheet from `'self'`, with no inline or third-party scripts.

Set `VITE_API_URL` in the Vercel project's Environment Variables to your
deployed backend. If it is unset or unreachable, the app still runs on bundled
demo data.

### Mock fallback

- Mock fixtures: `src/mocks/*.json` — shapes match the API in `design.md §9`
  and the examples in `/data/snapshots/examples`.
- The conditions and risk **grids** are generated deterministically over the
  study bbox in `src/mocks/index.ts`.

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
