/**
 * Fathom API client.
 *
 * Until the real FastAPI backend (design.md §9) exists, this resolves every
 * call from the mock layer. Set VITE_USE_MOCKS=false (with the backend running
 * behind the /api proxy, see vite.config.ts) to use real endpoints.
 */
import type {
  Conditions,
  MetaResponse,
  RiskCell,
  RoutePlan,
  ScenarioResult,
  Sighting,
  TripRequest,
  Zone,
} from './types';
import * as mock from '@/mocks';

/** True unless explicitly disabled via env. Mocks are the default. */
export const USE_MOCKS: boolean = import.meta.env.VITE_USE_MOCKS !== 'false';

const API_BASE = import.meta.env.VITE_API_BASE ?? '/api';

/** Simulate network latency so loading states are exercised in the demo. */
function delay<T>(value: T, ms = 180): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms));
}

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
  return (await res.json()) as T;
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`POST ${path} failed: ${res.status}`);
  return (await res.json()) as T;
}

export const api = {
  async getMeta(): Promise<MetaResponse> {
    if (USE_MOCKS) return delay(mock.meta);
    return getJson<MetaResponse>('/meta/sources');
  },

  async getZones(time: string): Promise<Zone[]> {
    if (USE_MOCKS) return delay(mock.zones);
    return getJson<Zone[]>(`/layers/zones?time=${encodeURIComponent(time)}`);
  },

  async getSightings(): Promise<Sighting[]> {
    if (USE_MOCKS) return delay(mock.sightings);
    return getJson<Sighting[]>('/layers/sightings');
  },

  async getConditions(time: string): Promise<Conditions[]> {
    if (USE_MOCKS) return delay(mock.conditionsGrid(time));
    return getJson<Conditions[]>(`/layers/conditions?time=${encodeURIComponent(time)}`);
  },

  async getRisk(time: string, speedKn: number): Promise<RiskCell[]> {
    if (USE_MOCKS) return delay(mock.riskGrid(time, speedKn));
    return getJson<RiskCell[]>(
      `/layers/risk?time=${encodeURIComponent(time)}&speed=${speedKn}`,
    );
  },

  async planTrip(req: TripRequest): Promise<RoutePlan[]> {
    if (USE_MOCKS) return delay(mock.routes, 500);
    return postJson<RoutePlan[]>('/trip/plan', req);
  },

  async runScenario(): Promise<ScenarioResult[]> {
    if (USE_MOCKS) return delay(mock.scenarios, 500);
    return postJson<ScenarioResult[]>('/sim/run', {});
  },
};
