/**
 * Mock data layer for Fathom.
 *
 * Provides fake-but-shape-accurate data matching the API responses in
 * design.md §9 so the frontend runs end-to-end before the real backend exists.
 * Grids (conditions, risk) are generated deterministically over the study bbox;
 * everything else is loaded from the JSON fixtures in this folder.
 *
 * When the real backend is available, flip USE_MOCKS to false (or set
 * VITE_USE_MOCKS=false) and the client in ../api/client.ts hits /api instead.
 */
import type {
  Conditions,
  MetaResponse,
  RiskCell,
  RoutePlan,
  ScenarioResult,
  Sighting,
  Zone,
} from '@/api/types';
import { STUDY_AREA } from '@/config/studyArea';

import metaJson from './meta.json';
import zonesJson from './zones.json';
import sightingsJson from './sightings.json';
import routesJson from './routes.json';
import scenariosJson from './scenarios.json';

export const meta = metaJson as MetaResponse;
export const zones = zonesJson as Zone[];
export const sightings = sightingsJson as Sighting[];
export const routes = routesJson as RoutePlan[];
export const scenarios = scenariosJson as ScenarioResult[];

const { bbox, cellDeg } = STUDY_AREA;
const [minLon, minLat, maxLon, maxLat] = bbox;

/** Cheap deterministic pseudo-noise so the same cell always looks the same. */
function hashNoise(a: number, b: number): number {
  const s = Math.sin(a * 127.1 + b * 311.7) * 43758.5453;
  return s - Math.floor(s); // 0..1
}

/** Smoothly varying field in [0,1] over the study area. */
function field(lon: number, lat: number, seed: number): number {
  const nx = (lon - minLon) / (maxLon - minLon);
  const ny = (lat - minLat) / (maxLat - minLat);
  const wave =
    0.5 +
    0.25 * Math.sin((nx * 3 + seed) * Math.PI) +
    0.25 * Math.cos((ny * 2 + seed) * Math.PI);
  return Math.min(1, Math.max(0, 0.7 * wave + 0.3 * hashNoise(lon + seed, lat)));
}

/** Rough land mask: treat the western coastal strip as land. */
function isLand(lon: number, lat: number): boolean {
  // Massachusetts coast roughly steps east as you go south; keep it simple.
  const coast = -70.9 + (lat - minLat) * 0.05;
  return lon < coast && lat > 41.9;
}

function cellId(ix: number, iy: number): string {
  return `${ix}_${iy}`;
}

interface GridPoint {
  ix: number;
  iy: number;
  lon: number;
  lat: number;
  land: boolean;
}

function* gridPoints(): Generator<GridPoint> {
  let iy = 0;
  for (let lat = minLat; lat <= maxLat + 1e-9; lat += cellDeg, iy++) {
    let ix = 0;
    for (let lon = minLon; lon <= maxLon + 1e-9; lon += cellDeg, ix++) {
      yield { ix, iy, lon: round(lon), lat: round(lat), land: isLand(lon, lat) };
    }
  }
}

function round(n: number): number {
  return Math.round(n * 1000) / 1000;
}

/**
 * Conditions grid for a given forecast time. Values drift slightly with the
 * hour so the time slider visibly changes the map.
 */
export function conditionsGrid(timeIso: string): Conditions[] {
  const hourSeed = (new Date(timeIso).getUTCHours() % 24) / 24;
  const out: Conditions[] = [];
  for (const p of gridPoints()) {
    if (p.land) continue;
    const wave = round(0.6 + 3.2 * field(p.lon, p.lat, 1.2 + hourSeed));
    const wind = round(6 + 26 * field(p.lon, p.lat, 2.7 + hourSeed));
    const sst = round(4 + 5 * field(p.lon, p.lat, 0.4));
    out.push({
      cell_id: cellId(p.ix, p.iy),
      time: timeIso,
      wave_m: wave,
      wind_kn: wind,
      sst_c: sst,
      source: meta.sources.find((s) => s.layer === 'conditions')?.source_url
        ? 'noaa_ndbc_44013'
        : 'synthetic',
      fetched_at: meta.data_timestamp,
      // Extra convenience fields for rendering (real API returns cell centroids).
      lon: p.lon,
      lat: p.lat,
    } as Conditions);
  }
  return out;
}

/** Vessel-speed lethality curve (design.md §5): logistic around v50 = 11.8 kn. */
export function lethality(speedKn: number): number {
  const v50 = 11.8;
  const k = 2.0;
  return 1 / (1 + Math.exp(-(speedKn - v50) / k));
}

/**
 * Whale-risk grid for a time + planned speed. Combines a smooth presence prior,
 * a sighting-recency term, and the speed lethality factor — a visual stand-in
 * for the deterministic backend model in design.md §5.
 */
export function riskGrid(timeIso: string, speedKn: number): RiskCell[] {
  const now = new Date(timeIso).getTime();
  const tauMs = 7 * 24 * 3600 * 1000; // 7-day decay
  const rhoDeg = 0.12; // ~10 km in degrees
  const leth = lethality(speedKn);

  const out: RiskCell[] = [];
  for (const p of gridPoints()) {
    if (p.land) continue;

    const presence = 0.55 * field(p.lon, p.lat, 3.3);

    // Recency: 1 - prod(1 - influence of each nearby sighting).
    let keep = 1;
    for (const s of sightings) {
      const d = Math.hypot(s.lon - p.lon, s.lat - p.lat);
      if (d > rhoDeg * 3) continue;
      const ageMs = Math.max(0, now - new Date(s.observed_at).getTime());
      const influence =
        Math.exp(-ageMs / tauMs) * Math.exp(-d / rhoDeg) * Math.min(1, s.count / 3);
      keep *= 1 - Math.min(0.95, influence);
    }
    const recency = 1 - keep;

    const pWhale = Math.min(1, Math.max(0, 0.6 * presence + 0.4 * recency));
    const risk = round(pWhale * leth);

    out.push({
      cell_id: cellId(p.ix, p.iy),
      lon: p.lon,
      lat: p.lat,
      risk,
      factors: {
        presence: round(presence),
        recency: round(recency),
        lethality: round(leth),
      },
    });
  }
  return out;
}
