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
