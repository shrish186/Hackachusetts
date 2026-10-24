import type { Language, VesselType } from '@/api/types';

/**
 * Shareable planner state encoded in the URL hash (item 4).
 *
 * Everything read from the hash is validated and clamped — never trusted.
 * Unknown values are ignored and fall back to a safe default.
 */
export interface PlannerState {
  port: string;
  vessel: VesselType;
  cruiseKn: number;
  maxHours: number;
  departure: string; // datetime-local value
  ground: string; // '' = Any
  riskPref: number;
  replay: boolean;
  language: Language;
}

const VESSELS: VesselType[] = ['small_boat', 'mid_trawler', 'scalloper'];
const LANGS: Language[] = ['en', 'pt', 'es'];

function clamp(n: number, lo: number, hi: number): number {
  return Math.max(lo, Math.min(hi, n));
}

/** Only ids made of [a-z0-9_,.\-] (ground may be "lon,lat"); length-capped. */
function safeId(v: string | null | undefined): string {
  if (!v) return '';
  const s = String(v).toLowerCase();
  return /^[a-z0-9_,.-]{1,40}$/.test(s) ? s : '';
}

/** datetime-local "YYYY-MM-DDTHH:mm" only. */
function safeDeparture(v: string | null | undefined): string | null {
  if (!v) return null;
  return /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(v) && !isNaN(new Date(v).getTime())
    ? v
    : null;
}

export function encodePlannerState(st: PlannerState): string {
  const p = new URLSearchParams();
  p.set('port', st.port);
  p.set('vessel', st.vessel);
  p.set('kn', String(st.cruiseKn));
  p.set('hrs', String(st.maxHours));
  p.set('dep', st.departure);
  if (st.ground) p.set('ground', st.ground);
  p.set('risk', st.riskPref.toFixed(2));
  p.set('replay', st.replay ? '1' : '0');
  p.set('lang', st.language);
  return p.toString();
}

/** Build a full shareable URL for the current origin + pathname. */
export function buildShareUrl(st: PlannerState): string {
  const base = `${window.location.origin}${window.location.pathname}`;
  return `${base}#plan=${encodeURIComponent(encodePlannerState(st))}`;
}

/**
 * Parse the planner state from the current hash, if present. Returns a partial
 * object with ONLY the fields that validated, so the caller can merge over its
 * own defaults.
 */
export function parsePlannerStateFromHash(hash: string): Partial<PlannerState> {
  const m = /[#&]plan=([^&]+)/.exec(hash);
  if (!m) return {};
  let params: URLSearchParams;
  try {
    params = new URLSearchParams(decodeURIComponent(m[1]));
  } catch {
    return {};
  }
  const out: Partial<PlannerState> = {};

  const port = safeId(params.get('port'));
  if (port) out.port = port;

  const vessel = params.get('vessel');
  if (vessel && VESSELS.includes(vessel as VesselType)) out.vessel = vessel as VesselType;

  const kn = Number(params.get('kn'));
  if (Number.isFinite(kn)) out.cruiseKn = clamp(Math.round(kn * 2) / 2, 4, 18);

  const hrs = Number(params.get('hrs'));
  if (Number.isFinite(hrs)) out.maxHours = clamp(Math.round(hrs), 1, 48);

  const dep = safeDeparture(params.get('dep'));
  if (dep) out.departure = dep;

  const ground = safeId(params.get('ground'));
  if (ground) out.ground = ground;

  const risk = Number(params.get('risk'));
  if (Number.isFinite(risk)) out.riskPref = clamp(Math.round(risk * 10) / 10, 0, 1);

  const replay = params.get('replay');
  if (replay === '1' || replay === '0') out.replay = replay === '1';

  const lang = params.get('lang');
  if (lang && LANGS.includes(lang as Language)) out.language = lang as Language;

  return out;
}
