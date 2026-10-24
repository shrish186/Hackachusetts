/**
 * Fathom API client.
 *
 * Until the real FastAPI backend (design.md §9) exists, this resolves every
 * call from the mock layer. Set VITE_USE_MOCKS=false (with the backend running
 * behind the /api proxy, see vite.config.ts) to use real endpoints.
 */
import type {
  AgentEvent,
  Conditions,
  Language,
  MetaResponse,
  RiskCell,
  RoutePlan,
  ScenarioResult,
  Sighting,
  TripRequest,
  Zone,
} from './types';
import * as mock from '@/mocks';

/** Plain-language label per tool, by language (for the live agent feed). */
const TOOL_LABELS: Record<Language, Record<string, string>> = {
  en: {
    get_conditions: 'Checking weather and sea state…',
    get_zones: 'Checking protection zones…',
    get_whale_risk: 'Checking whale risk…',
    get_effort_proxy: 'Checking fishing access…',
    plan_routes: 'Planning routes…',
    estimate_fuel: 'Estimating fuel…',
  },
  pt: {
    get_conditions: 'Verificando clima e estado do mar…',
    get_zones: 'Verificando zonas de proteção…',
    get_whale_risk: 'Verificando risco de baleia…',
    get_effort_proxy: 'Verificando acesso à pesca…',
    plan_routes: 'Planejando rotas…',
    estimate_fuel: 'Estimando combustível…',
  },
  es: {
    get_conditions: 'Revisando clima y estado del mar…',
    get_zones: 'Revisando zonas de protección…',
    get_whale_risk: 'Revisando riesgo de ballena…',
    get_effort_proxy: 'Revisando acceso a pesca…',
    plan_routes: 'Planificando rutas…',
    estimate_fuel: 'Estimando combustible…',
  },
};

export interface PlanStreamCallbacks {
  onEvent: (event: AgentEvent) => void;
  signal?: AbortSignal;
}

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

  /**
   * Plan a trip while streaming the agent's tool-call steps to the UI
   * (requirements.md Req 4.5). In mock mode this replays the scripted
   * agentScript with small delays; against the real backend this would read
   * an SSE stream from POST /api/trip/plan. Resolves to the ranked plans.
   */
  async planTripStream(
    req: TripRequest,
    cb: PlanStreamCallbacks,
  ): Promise<RoutePlan[]> {
    if (USE_MOCKS) {
      const labels = TOOL_LABELS[req.language] ?? TOOL_LABELS.en;
      for (const step of mock.agentScript) {
        if (cb.signal?.aborted) break;
        cb.onEvent({
          id: step.id,
          tool: step.tool,
          label: labels[step.tool] ?? step.tool,
          status: 'running',
        });
        await delay(null, 420);
        if (cb.signal?.aborted) break;
        cb.onEvent({
          id: step.id,
          tool: step.tool,
          label: labels[step.tool] ?? step.tool,
          status: 'done',
          detail: step.detail,
        });
      }
      return delay(mock.routes, 250);
    }
    // Real backend: fall back to the non-streaming endpoint for now.
    return postJson<RoutePlan[]>('/trip/plan', req);
  },

  async runScenario(): Promise<ScenarioResult[]> {
    if (USE_MOCKS) return delay(mock.scenarios, 500);
    return postJson<ScenarioResult[]>('/sim/run', {});
  },
};
