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
  Port,
  Ground,
  RiskCell,
  RoutePlan,
  ScenarioListItem,
  ScenarioResult,
  ScenarioRunResult,
  Sighting,
  SourceMeta,
  TripRequest,
  Zone,
} from './types';
import * as mock from '@/mocks';
import { bundledPorts } from '@/data/ports';
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

export type ConnState = 'unknown' | 'online' | 'waking' | 'offline';

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

/* Cold-start grace window (item 4): for the first 60 s of failures we show a
 * neutral "waking" state, not the red "offline" badge. `firstFailureAt` is the
 * timestamp of the earliest failure in the current outage; it resets on any
 * success. Only once failures persist past the window do we flip to offline. */
const COLD_START_MS = 60_000;
let firstFailureAt: number | null = null;

/** Called on any successful response: we're online; clear the outage clock. */
function markOnline(): void {
  firstFailureAt = null;
  setConn('online');
}

/**
 * Called on any failed/timed-out call. Within the 60 s grace window we stay in
 * "waking" (neutral); after it we go "offline" (red badge).
 */
function markFailure(): void {
  const now = Date.now();
  if (firstFailureAt == null) firstFailureAt = now;
  if (connState === 'online') firstFailureAt = now; // outage just started
  setConn(now - firstFailureAt < COLD_START_MS ? 'waking' : 'offline');
}

/** Mark that we are waiting on a possibly-cold free-tier server. */
export function setWaking(): void {
  if (connState !== 'online') setConn('waking');
}

/**
 * Probe GET /api/health. Resolves true on a real 200 response. Used by the
 * offline banner's retry loop (every 5 s) to auto-recover to Live. A short
 * per-probe timeout keeps the 5 s cadence snappy; the 60 s grace is tracked by
 * markFailure, not this timeout.
 */
export async function pingHealth(timeoutMs = 8000): Promise<boolean> {
  const ac = new AbortController();
  const timer = setTimeout(() => ac.abort(), timeoutMs);
  if (connState !== 'online') setWaking();
  try {
    const res = await fetch(`${API_URL}/api/health`, { signal: ac.signal });
    if (!res.ok) throw new Error(`health -> ${res.status}`);
    await res.json().catch(() => ({}));
    markOnline();
    return true;
  } catch {
    markFailure();
    return false;
  } finally {
    clearTimeout(timer);
  }
}

/* -------------------------------------------------------------------------- */
/* Low-level fetch with timeout                                               */
/* -------------------------------------------------------------------------- */

/** Error carrying the HTTP status so callers can show 429/504 messages. */
export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

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
    if (!res.ok) {
      // The server did respond, so the connection is up (helps 429/504 flows).
      markOnline();
      throw new ApiError(res.status, `${path} -> ${res.status}`);
    }
    const json = (await res.json()) as T;
    markOnline();
    return json;
  } catch (err) {
    // A real HTTP error means the server answered -> still online. Only
    // network/timeout failures count toward the cold-start outage clock.
    if (!(err instanceof ApiError)) markFailure();
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

/** Normalize a port object (tolerant of missing/extra fields). */
function adaptPort(raw: unknown): Port {
  const o = raw as Record<string, unknown>;
  const grounds = Array.isArray(o.grounds) ? o.grounds : [];
  return {
    id: String(o.id ?? ''),
    name: String(o.name ?? o.id ?? ''),
    lon: Number(o.lon),
    lat: Number(o.lat),
    grounds: grounds.map((g): Ground => {
      const x = g as Record<string, unknown>;
      return {
        id: String(x.id ?? ''),
        name: String(x.name ?? x.id ?? ''),
        lon: Number(x.lon),
        lat: Number(x.lat),
        closed: Boolean(x.closed),
        closed_reason: (x.closed_reason as string | undefined) ?? undefined,
        closed_from: (x.closed_from as string | null | undefined) ?? null,
        closed_to: (x.closed_to as string | null | undefined) ?? null,
      };
    }),
  };
}

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

/** Pull a number from a record under any of the given keys, else null. */
function numOrNull(obj: Record<string, unknown> | undefined, ...keys: string[]): number | null {
  if (!obj) return null;
  for (const k of keys) {
    const v = obj[k];
    if (typeof v === 'number') return v;
  }
  return null;
}

/**
 * Map the /api/sim/run response `{ baseline, options:[...] }` into the shape the
 * UI uses. `deltas_pct.{risk,hours,fuel,effort_access}` map to delta_* fields;
 * the localized summary is picked by language. Also surfaces baseline access
 * loss (item 6) and per-option access-lost trips (item 4).
 */
function adaptScenarioRun(raw: unknown, language: Language): ScenarioRunResult {
  const root = raw as Record<string, unknown>;
  const baseline = (root.baseline ?? {}) as Record<string, unknown>;
  const options = Array.isArray(root.options) ? root.options : [];
  const results: ScenarioResult[] = options.map((o) => {
    const opt = o as Record<string, unknown>;
    const d = (opt.deltas_pct ?? {}) as Record<string, number>;
    const totals = (opt.totals ?? {}) as Record<string, unknown>;
    const summary = opt.summary as Record<string, string> | string | undefined;
    const summaryText =
      typeof summary === 'string'
        ? summary
        : (summary?.[language] ?? summary?.en ?? '');
    return {
      scenario_id: String(opt.scenario_id ?? opt.id ?? ''),
      label: String(opt.name ?? opt.label ?? opt.scenario_id ?? ''),
      delta_risk_pct: Number(d.risk ?? 0),
      delta_hours_pct: Number(d.hours ?? 0),
      delta_fuel_pct: Number(d.fuel ?? 0),
      delta_effort_access_pct: Number(d.effort_access ?? 0),
      on_frontier: Boolean(opt.on_frontier),
      summary: summaryText,
      access_lost_trips: numOrNull(opt, 'access_lost_trips') ?? numOrNull(totals, 'access_lost_trips'),
    };
  });
  return {
    results,
    baselineAccessLost: numOrNull(baseline, 'access_lost_trips', 'access_lost'),
    baselineTrips: numOrNull(baseline, 'trips'),
  };
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

/** Access-lost info when the target ground / port is unreachable (item 4). */
export interface AccessLost {
  endpoint: string; // "destination" | "origin"
  code: string; // "closed_zone" | "land" | "outside" | "no_water"
  reason?: string;
  zone_id?: string;
  zone_name?: string;
  zone_active_to?: string;
  nearest_open?: { lon: number; lat: number; distance_nm: number } | null;
}

export interface PlanResult {
  plans: RoutePlan[];
  narrative: NarrativeLine[];
  disclaimer: string | null;
  /** Set when no legal route exists; names the constraint to relax. */
  message: string | null;
  /** Present when the target ground (or port) is closed/unreachable. */
  access_lost: AccessLost | null;
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
    access_lost: null,
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

  /**
   * Ports + their fishing grounds (GET /api/meta/ports, item 1). Accepts an
   * optional time so the backend can mark grounds closed at that instant.
   * Falls back to the bundled list in src/data/ports.ts on 404 / failure.
   */
  async getPorts(time?: string): Promise<Port[]> {
    return withFallback(
      async () => {
        const q = time ? `?time=${encodeURIComponent(time)}` : '';
        const raw = await fetchJson<unknown>(`/api/meta/ports${q}`);
        const arr = (Array.isArray(raw)
          ? raw
          : (raw as { ports?: unknown[] }).ports ?? []) as Port[];
        return arr.length ? arr.map(adaptPort) : bundledPorts(time);
      },
      () => bundledPorts(time),
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
      // Allow a free-tier cold start: wait up to 60 s for the first byte.
      const timer = setTimeout(() => ac.abort(), 60_000);
      if (cb.signal) cb.signal.addEventListener('abort', () => ac.abort(), { once: true });
      setWaking();

      const res = await fetch(`${API_URL}/api/trip/plan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
        body: JSON.stringify(req),
        signal: ac.signal,
      });
      clearTimeout(timer);
      if (!res.ok || !res.body) throw new Error(`trip/plan -> ${res.status}`);
      markOnline();
      return await consumeSse(res.body, cb);
    } catch {
      markFailure();
      return replayMockStream(req, cb);
    }
  },

  /**
   * List selectable scenarios (GET /api/sim/scenarios). The contract returns
   * `{ scenarios: [{ id, name, description }] }`; map to ScenarioListItem.
   */
  async getScenarios(): Promise<ScenarioListItem[]> {
    return withFallback(
      async () => {
        const raw = await fetchJson<unknown>('/api/sim/scenarios');
        const arr = (Array.isArray(raw)
          ? raw
          : (raw as { scenarios?: unknown[] }).scenarios ?? []) as Record<string, unknown>[];
        const mapped = arr.map((o) => ({
          scenario_id: String(o.id ?? o.scenario_id ?? ''),
          label: String(o.name ?? o.label ?? o.id ?? ''),
          description: (o.description as string | undefined) ?? undefined,
          synthetic: true,
        }));
        return mapped.length ? mapped : mock.scenarioList;
      },
      () => mock.scenarioList,
    );
  },

  /**
   * Run the fleet re-route simulation (POST /api/sim/run). Pass a scenario id
   * (the backend runs all preloaded options so the frontier is meaningful), or
   * a custom drawn polygon as a candidate zone. Returns localized
   * ScenarioResult[]. Can time out / be cancelled via the caller's signal;
   * throws ApiError on 429/504 so the UI can show friendly messages.
   */
  async runScenario(opts?: {
    scenarioId?: string;
    polygon?: Array<[number, number]>;
    /** Closure (no entry) vs. a speed limit for the custom polygon (item 5). */
    prohibited?: boolean;
    /** Speed cap in knots when not a full closure (null for closure). */
    speedLimitKn?: number | null;
    language?: Language;
    signal?: AbortSignal;
    timeoutMs?: number;
  }): Promise<ScenarioRunResult> {
    const language = opts?.language ?? 'en';
    const body: Record<string, unknown> = {};
    if (opts?.polygon && opts.polygon.length >= 3) {
      // Candidate polygon as a closed GeoJSON ring (item 5).
      body.polygon = {
        type: 'Polygon',
        coordinates: [[...opts.polygon, opts.polygon[0]]],
      };
      const prohibited = opts.prohibited ?? true;
      body.prohibited = prohibited;
      body.speed_limit_kn = prohibited ? null : (opts.speedLimitKn ?? 10);
    } else if (opts?.scenarioId) {
      body.scenario_id = opts.scenarioId;
    }
    const raw = await fetchJson<unknown>('/api/sim/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: opts?.signal,
      timeoutMs: opts?.timeoutMs ?? 60_000,
    });
    return adaptScenarioRun(raw, language);
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
      markOnline();
      return await res.text();
    } catch {
      markFailure();
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
  const result: PlanResult = {
    plans: mock.routes,
    narrative: [],
    disclaimer: null,
    message: null,
    access_lost: null,
  };
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
        result.access_lost = (msg.access_lost as AccessLost | null) ?? null;
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
