/**
 * Time helpers. All timestamps are UTC internally; display in America/New_York
 * (tech steering).
 */

/** The demo forecast window: a 48-hour span of 3-hour slices (design.md §6). */
export const DEMO_START_ISO = '2026-03-14T00:00:00Z';
export const SLICE_HOURS = 3;
export const SLICE_COUNT = 16; // 48h / 3h

/** ISO timestamp for slice index [0, SLICE_COUNT). */
export function sliceToIso(index: number): string {
  const start = new Date(DEMO_START_ISO).getTime();
  return new Date(start + index * SLICE_HOURS * 3600 * 1000).toISOString();
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
