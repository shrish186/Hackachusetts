/**
 * Fathom API client.
 *
 * Talks to the real FastAPI backend at VITE_API_URL (default
 * http://localhost:8000). Every request has a 4-second timeout; if a request
 * fails or times out, the client falls back to the bundled mock data and marks
 * the connection "offline" so the UI can show an "Offline demo data" badge.
 *
 * The backend currently wraps layer responses as
 * `{ layer, provenance, count, features|cells }`; this client normalizes those
 * into the clean types in ./types.ts (the source of truth until
 * docs/API_CONTRACT.md exists). Endpoints the backend does not implement yet
 * (/trip/plan SSE, /sim/*, /trip/brief) fall back to mocks transparently.
 */
import type {
  AgentEvent,
  Conditions,
  Language,
  MetaResponse,
  RiskCell,
  RoutePlan,
  ScenarioListItem,
  ScenarioResult,
  Sighting,
  SourceMeta,
  TripRequest,
  Zone,
} from './types';
import * as mock from '@/mocks';
import { STUDY_AREA } from '@/config/studyArea';

/* -------------------------------------------------------------------------- */
/* Config                                                                     */
/* -------------------------------------------------------------------------- */

/** Base URL of the backend API. */
export const API_URL: string =
  (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, '') ??
  'http://localhost:8000';

/** Per-request timeout. If exceeded we fall back to mocks. */
const TIMEOUT_MS = 4000;

const BBOX = STUDY_AREA.bbox.join(',');

/* -------------------------------------------------------------------------- */
/* Connection status (observable, for the "Offline demo data" badge)          */
/* -------------------------------------------------------------------------- */

export type ConnState = 'unknown' | 'online' | 'offline';

let connState: ConnState = 'unknown';
const listeners = new Set<(s: ConnState) => void>();

export function getConnState(): ConnState {
  return connState;
}

export function subscribeConn(fn: (s: ConnState) => void): () => void {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

function setConn(next: ConnState) {
  if (connState === next) return;
  connState = next;
  listeners.forEach((fn) => fn(next));
}

/* -------------------------------------------------------------------------- */
/* Low-level fetch with timeout                                               */
/* -------------------------------------------------------------------------- */

async function fetchJson<T>(
  path: string,
  init?: RequestInit & { timeoutMs?: number },
): Promise<T> {
  const ac = new AbortController();
  const timeoutMs = init?.timeoutMs ?? TIMEOUT_MS;
  const timer = setTimeout(() => ac.abort(), timeoutMs);
  // Chain any caller-provided signal into our abort controller.
  if (init?.signal) {
    if (init.signal.aborted) ac.abort();
    else init.signal.addEventListener('abort', () => ac.abort(), { once: true });
  }
  try {
    const res = await fetch(`${API_URL}${path}`, { ...init, signal: ac.signal });
    if (!res.ok) throw new Error(`${path} -> ${res.status}`);
    const json = (await res.json()) as T;
    setConn('online');
    return json;
  } catch (err) {
    setConn('offline');
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

/** Resolve a promise, or the fallback value if it rejects/times out. */
async function withFallback<T>(
  attempt: () => Promise<T>,
  fallback: () => T | Promise<T>,
): Promise<T> {
  try {
    return await attempt();
  } catch {
    return fallback();
  }
}

function delay<T>(value: T, ms = 150): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms));
}

/* -------------------------------------------------------------------------- */
/* Response adapters (backend wrapped shape -> clean types)                   */
/* -------------------------------------------------------------------------- */

function adaptMeta(raw: unknown): MetaResponse {
  const r = raw as { demo_mode?: boolean; sources?: unknown[]; data_timestamp?: string };
  const sources: SourceMeta[] = (r.sources ?? []).map((s) => {
    const o = s as Record<string, unknown>;
    return {
      layer: String(o.layer ?? o.name ?? 'unknown'),
      source_url: (o.source_url as string | null) ?? null,
      fetched_at: (o.fetched_at as string | null) ?? null,
      cached: Boolean(o.cached),
      synthetic: Boolean(o.synthetic),
    };
  });
  // Pick the newest fetched_at as the data timestamp, if any.
  const stamps = sources
    .map((s) => s.fetched_at)
    .filter((t): t is string => !!t)
    .sort();
  return {
    demo_mode: Boolean(r.demo_mode),
    sources,
    data_timestamp: r.data_timestamp ?? stamps[stamps.length - 1] ?? new Date().toISOString(),
  };
}

/** Extract the item array from a layer envelope `{ items: [...] }`. */
function items(raw: unknown): Record<string, unknown>[] {
  const o = raw as { items?: unknown[] };
  if (Array.isArray(o.items)) return o.items as Record<string, unknown>[];
  if (Array.isArray(raw)) return raw as Record<string, unknown>[];
  return [];
}

function adaptZones(raw: unknown): Zone[] {
  return items(raw).map((z) => ({
    id: String(z.id),
    name: String(z.name ?? z.id),
    kind: z.kind as Zone['kind'],
    geometry: z.geometry as Zone['geometry'],
    active_from: (z.active_from as string | null) ?? null,
    active_to: (z.active_to as string | null) ?? null,
    speed_limit_kn: (z.speed_limit_kn as number | null) ?? null,
    prohibited: Boolean(z.prohibited),
    source_url: String(z.source_url ?? ''),
    source_updated: String(z.source_updated ?? ''),
    synthetic: z.synthetic as boolean | undefined,
  }));
}

function adaptConditions(raw: unknown): Conditions[] {
  return items(raw) as unknown as Conditions[];
}

function adaptRisk(raw: unknown): RiskCell[] {
  return items(raw).map((c, i) => {
    const factors = (c.factors ?? {}) as Record<string, number>;
    return {
      cell_id: String(c.cell_id ?? `${i}`),
      lon: Number(c.lon),
      lat: Number(c.lat),
      risk: Number(c.risk),
      factors: {
        presence: Number(factors.presence ?? 0),
        recency: Number(factors.recency ?? 0),
        lethality: Number(factors.lethality ?? 0),
      },
    };
  });
}

/* -------------------------------------------------------------------------- */
/* Agent feed tool labels                                                     */
/* -------------------------------------------------------------------------- */

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

/** A plain-language narrative line with its supporting tool-call citations. */
export interface NarrativeLine {
  text: string;
  citations: string[];
}

export interface PlanResult {
  plans: RoutePlan[];
  narrative: NarrativeLine[];
  disclaimer: string | null;
  /** Set when no legal route exists; names the constraint to relax. */
  message: string | null;
}

export interface PlanStreamCallbacks {
  onEvent: (event: AgentEvent) => void;
  signal?: AbortSignal;
}

/** Replay the scripted mock agent feed (used when the SSE backend is down). */
async function replayMockStream(
  req: TripRequest,
  cb: PlanStreamCallbacks,
): Promise<PlanResult> {
  const labels = TOOL_LABELS[req.language] ?? TOOL_LABELS.en;
  for (const step of mock.agentScript) {
    if (cb.signal?.aborted) break;
    cb.onEvent({ id: step.id, tool: step.tool, label: labels[step.tool] ?? step.tool, status: 'running' });
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
  await delay(null, 200);
  return {
    plans: mock.routes,
    narrative: mock.narrativeFor(req.language),
    disclaimer: null,
    message: null,
  };
}

/* -------------------------------------------------------------------------- */
/* Public API                                                                 */
/* -------------------------------------------------------------------------- */

export const api = {
  async getMeta(): Promise<MetaResponse> {
    return withFallback(
      async () => adaptMeta(await fetchJson('/api/meta/sources')),
      () => mock.meta,
    );
  },

  async getZones(time: string): Promise<Zone[]> {
    return withFallback(
      async () =>
        adaptZones(await fetchJson(`/api/layers/zones?bbox=${BBOX}&time=${encodeURIComponent(time)}`)),
      () => mock.zones,
    );
  },

  async getSightings(): Promise<Sighting[]> {
    // No dedicated sightings layer endpoint in the contract; use the bundled
    // sample (also synthetic on the backend).
    return withFallback(
      async () => {
        const raw = await fetchJson<unknown>(`/api/layers/sightings?bbox=${BBOX}`);
        const arr = items(raw) as unknown as Sighting[];
        return arr.length ? arr : mock.sightings;
      },
      () => mock.sightings,
    );
  },

  /** Conditions grid. From the API when up; otherwise the in-browser mock. */
  async getConditions(time: string): Promise<Conditions[]> {
    return withFallback(
      async () => {
        const data = adaptConditions(
          await fetchJson(`/api/layers/conditions?bbox=${BBOX}&time=${encodeURIComponent(time)}`),
        );
        return data.length ? data : mock.conditionsGrid(time);
      },
      () => mock.conditionsGrid(time),
    );
  },

  /** Risk grid. From the API when up; otherwise the in-browser generator. */
  async getRisk(time: string, speedKn: number): Promise<RiskCell[]> {
    return withFallback(
      async () => {
        const data = adaptRisk(
          await fetchJson(`/api/layers/risk?bbox=${BBOX}&time=${encodeURIComponent(time)}&speed=${speedKn}`),
        );
        return data.length ? data : mock.riskGrid(time, speedKn);
      },
      () => mock.riskGrid(time, speedKn),
    );
  },

  async planTrip(req: TripRequest): Promise<RoutePlan[]> {
    return withFallback(
      () => fetchJson<RoutePlan[]>('/api/trip/plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req),
      }),
      () => mock.routes,
    );
  },

  /**
   * Plan a trip, streaming the agent's tool calls to the UI via Server-Sent
   * Events (requirements.md Req 4.5). Reads POST /api/trip/plan as a stream
   * with fetch; on any failure it replays the scripted mock feed instead.
   */
  async planTripStream(req: TripRequest, cb: PlanStreamCallbacks): Promise<PlanResult> {
    try {
      const ac = new AbortController();
      // Only time out the initial response; the stream itself may run longer.
      const timer = setTimeout(() => ac.abort(), TIMEOUT_MS);
      if (cb.signal) cb.signal.addEventListener('abort', () => ac.abort(), { once: true });

      const res = await fetch(`${API_URL}/api/trip/plan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
        body: JSON.stringify(req),
        signal: ac.signal,
      });
      clearTimeout(timer);
      if (!res.ok || !res.body) throw new Error(`trip/plan -> ${res.status}`);
      setConn('online');
      return await consumeSse(res.body, cb);
    } catch {
      setConn('offline');
      return replayMockStream(req, cb);
    }
  },

  /** List selectable scenarios (GET /api/sim/scenarios). */
  async getScenarios(): Promise<ScenarioListItem[]> {
    return withFallback(
      async () => {
        const raw = await fetchJson<unknown>('/api/sim/scenarios');
        const arr = (Array.isArray(raw) ? raw : (raw as { scenarios?: unknown[] }).scenarios ?? []) as ScenarioListItem[];
        return arr.length ? arr : mock.scenarioList;
      },
      () => mock.scenarioList,
    );
  },

  /**
   * Run the fleet re-route simulation (POST /api/sim/run). Pass scenario ids
   * to run a subset; pass a drawn polygon so the backend can treat it as a
   * candidate zone. Returns ScenarioResult[]; falls back to mock numbers.
   */
  async runScenario(opts?: {
    scenarioIds?: string[];
    polygon?: Array<[number, number]>;
  }): Promise<ScenarioResult[]> {
    return withFallback(
      async () => {
        const body: Record<string, unknown> = {};
        if (opts?.scenarioIds) body.scenario_ids = opts.scenarioIds;
        if (opts?.polygon) body.polygon = opts.polygon;
        const raw = await fetchJson<unknown>('/api/sim/run', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        });
        const arr = (Array.isArray(raw) ? raw : (raw as { results?: unknown[] }).results ?? []) as ScenarioResult[];
        return arr.length ? arr : mock.scenarios;
      },
      () => mock.scenarios,
    );
  },

  /**
   * Fetch a printable HTML brief for a plan (POST /api/trip/brief). Returns the
   * HTML string, or null if the backend is unreachable (caller builds it
   * client-side instead).
   */
  async getBriefHtml(plan: RoutePlan, language: Language, trip?: TripRequest): Promise<string | null> {
    try {
      const ac = new AbortController();
      const timer = setTimeout(() => ac.abort(), TIMEOUT_MS);
      const res = await fetch(`${API_URL}/api/trip/brief`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'text/html' },
        body: JSON.stringify({ plan, language, trip: trip ?? null }),
        signal: ac.signal,
      });
      clearTimeout(timer);
      if (!res.ok) throw new Error(`brief -> ${res.status}`);
      setConn('online');
      return await res.text();
    } catch {
      setConn('offline');
      return null;
    }
  },
};

/* -------------------------------------------------------------------------- */
/* SSE parsing for the trip planner stream                                    */
/* -------------------------------------------------------------------------- */

/**
 * Consume the trip planner SSE stream per docs/API_CONTRACT.md. Each frame is
 * `event: <name>` + one `data:` JSON line. We handle:
 *   tool_call   -> agent feed step (status running)
 *   tool_result -> agent feed step (status done, with detail)
 *   plans       -> { plans, narrative, disclaimer, message }
 *   done / error
 * Returns the final PlanResult (empty plans + message when no legal route).
 */
async function consumeSse(
  body: ReadableStream<Uint8Array>,
  cb: PlanStreamCallbacks,
): Promise<PlanResult> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  const result: PlanResult = { plans: mock.routes, narrative: [], disclaimer: null, message: null };
  let gotPlans = false;

  const handleFrame = (frame: string) => {
    let eventName = 'message';
    const dataParts: string[] = [];
    for (const line of frame.split('\n')) {
      if (line.startsWith('event:')) eventName = line.slice(6).trim();
      else if (line.startsWith('data:')) dataParts.push(line.slice(5).trim());
    }
    const dataStr = dataParts.join('\n');
    if (!dataStr) return;
    let msg: Record<string, unknown>;
    try {
      msg = JSON.parse(dataStr) as Record<string, unknown>;
    } catch {
      return;
    }

    switch (eventName) {
      case 'tool_call':
      case 'tool_result':
        cb.onEvent({
          id: String(msg.id ?? msg.tool),
          tool: String(msg.tool ?? 'tool'),
          label: String(msg.label ?? msg.tool ?? 'Working…'),
          status:
            (msg.status as AgentEvent['status']) ??
            (eventName === 'tool_result' ? 'done' : 'running'),
          detail: msg.detail as string | undefined,
        });
        break;
      case 'plans':
        gotPlans = true;
        result.plans = (msg.plans as RoutePlan[]) ?? [];
        result.narrative = (msg.narrative as NarrativeLine[]) ?? [];
        result.disclaimer = (msg.disclaimer as string | null) ?? null;
        result.message = (msg.message as string | null) ?? null;
        break;
      case 'error':
        cb.onEvent({
          id: 'error',
          tool: 'error',
          label: String(msg.error ?? 'Error'),
          status: 'error',
        });
        break;
      default:
        break;
    }
  };

  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let sep: number;
    while ((sep = buffer.indexOf('\n\n')) !== -1) {
      handleFrame(buffer.slice(0, sep));
      buffer = buffer.slice(sep + 2);
    }
  }
  if (buffer.trim()) handleFrame(buffer);

  // If the backend streamed tool events but never sent plans, keep mock routes
  // as a safety net so the UI still shows something.
  if (!gotPlans) result.plans = mock.routes;
  return result;
}
