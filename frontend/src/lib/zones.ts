import type { Zone, ZoneKind } from '@/api/types';

/** Theme color per zone kind (hex, used for both map fill and legend). */
export const ZONE_COLORS: Record<ZoneKind, string> = {
  whale_sma: '#39b7d6', // surf blue
  slow_zone: '#f2994a', // coral (caution)
  fishing_closure: '#e5544b', // alert (prohibited)
  wind_lease: '#8b7fd6', // violet
  wind_construction: '#e5544b', // alert (active exclusion)
};

export const ZONE_LABELS: Record<ZoneKind, string> = {
  whale_sma: 'Whale seasonal mgmt area',
  slow_zone: 'Slow zone',
  fishing_closure: 'Fishing closure',
  wind_lease: 'Wind lease area',
  wind_construction: 'Wind construction',
};

/** Is the zone active at the given time? Null dates mean "always". */
export function isZoneActive(zone: Zone, iso: string): boolean {
  const t = new Date(iso).getTime();
  const from = zone.active_from ? new Date(zone.active_from).getTime() : -Infinity;
  const to = zone.active_to ? new Date(zone.active_to).getTime() : Infinity;
  return t >= from && t <= to;
}

/** Restriction summary line for popups. */
export function restrictionSummary(zone: Zone): string {
  if (zone.prohibited) return 'No entry while active.';
  if (zone.speed_limit_kn != null) return `Speed limit ${zone.speed_limit_kn} kn while active.`;
  return 'Advisory area — check the source notice.';
}
