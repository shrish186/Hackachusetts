/**
 * Time helpers. All timestamps are UTC internally; display in America/New_York
 * (tech steering).
 */

/** The demo forecast window: a 48-hour span of 3-hour slices (design.md §6). */
export const DEMO_START_ISO = '2026-03-14T00:00:00Z';
/** Replay-mode window start: the slider's left end is 2026-03-15 (item A). */
export const REPLAY_START_ISO = '2026-03-15T00:00:00Z';
export const SLICE_HOURS = 3;
export const SLICE_COUNT = 16; // 48h / 3h

/**
 * "Replay whale season" instant — 2026-03-15T13:00:00Z == 9:00 AM EDT
 * (config/demo_scenarios.yaml → replay_whale_season.time_utc). On this date the
 * Cape Cod Bay / Off Race Point SMAs, the Stellwagen slow zone and the western
 * Gulf of Maine closure are all active, so the map shows real closures.
 */
export const REPLAY_WHALE_SEASON_ISO = '2026-03-15T13:00:00Z';

/** UTC ISO of the window's left end. Replay starts the window at 2026-03-15. */
export function windowStartIso(replay = false): string {
  return replay ? REPLAY_START_ISO : DEMO_START_ISO;
}

/** ISO timestamp for slice index [0, SLICE_COUNT) within the active window. */
export function sliceToIso(index: number, replay = false): string {
  const start = new Date(windowStartIso(replay)).getTime();
  const clamped = Math.max(0, Math.min(SLICE_COUNT - 1, index));
  return new Date(start + clamped * SLICE_HOURS * 3600 * 1000).toISOString();
}

/** Nearest slice index to a given UTC instant (clamped to [0, SLICE_COUNT-1]). */
export function isoToSlice(iso: string, replay = false): number {
  const start = new Date(windowStartIso(replay)).getTime();
  const t = new Date(iso).getTime();
  if (isNaN(t)) return 0;
  const idx = Math.round((t - start) / (SLICE_HOURS * 3600 * 1000));
  return Math.max(0, Math.min(SLICE_COUNT - 1, idx));
}

const NY_FMT = new Intl.DateTimeFormat('en-US', {
  timeZone: 'America/New_York',
  weekday: 'short',
  hour: 'numeric',
  minute: '2-digit',
  timeZoneName: 'short',
});

const NY_FMT_SHORT = new Intl.DateTimeFormat('en-US', {
  timeZone: 'America/New_York',
  month: 'short',
  day: 'numeric',
  hour: 'numeric',
  minute: '2-digit',
});

/** "Sat 2:00 PM EDT" */
export function formatLocal(iso: string): string {
  return NY_FMT.format(new Date(iso));
}

/** "Mar 14, 2:00 PM" */
export function formatLocalShort(iso: string): string {
  return NY_FMT_SHORT.format(new Date(iso));
}

const DATETIME_LONG = new Intl.DateTimeFormat('en-GB', {
  weekday: 'short',
  day: 'numeric',
  month: 'short',
  hour: 'numeric',
  minute: '2-digit',
  hour12: true,
});

/** Unambiguous local label, e.g. "Sat 24 Oct, 7:00 PM". */
export function formatDepartureLabel(d: Date): string {
  // en-GB gives "Sat, 24 Oct, 7:00 pm"; tidy to "Sat 24 Oct, 7:00 PM".
  return DATETIME_LONG.format(d)
    .replace(/^(\w{3}),\s*/, '$1 ')
    .replace(/\b(am|pm)\b/, (m) => m.toUpperCase());
}

/** Round a Date up to the next 30-minute mark (local time). */
export function roundUpToHalfHour(d: Date): Date {
  const out = new Date(d);
  out.setSeconds(0, 0);
  const m = out.getMinutes();
  const add = m === 0 || m === 30 ? 0 : m < 30 ? 30 - m : 60 - m;
  out.setMinutes(m + add);
  return out;
}

/** Default departure: now + 2 h, rounded up to the next 30 min (local). */
export function defaultDeparture(now: Date = new Date()): Date {
  return roundUpToHalfHour(new Date(now.getTime() + 2 * 3600 * 1000));
}

/**
 * Format a Date for an <input type="datetime-local"> value (local wall-clock,
 * no timezone): "YYYY-MM-DDTHH:mm".
 */
export function toDatetimeLocalValue(d: Date): string {
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`;
}

/** A datetime-local value (local wall-clock) → UTC ISO instant. */
export function datetimeLocalToIso(value: string): string {
  const d = new Date(value);
  return isNaN(d.getTime()) ? new Date().toISOString() : d.toISOString();
}

/** A UTC ISO instant → datetime-local value in the browser's local time. */
export function isoToDatetimeLocal(iso: string): string {
  return toDatetimeLocalValue(new Date(iso));
}
