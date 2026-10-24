import type { Port, Ground } from '@/api/types';

/**
 * Bundled fallback for GET /api/meta/ports (item 1). Used until that endpoint
 * exists (404) or when the backend is unreachable. Names and coordinates come
 * from config/ports.yaml (real, published harbor/ground locations).
 *
 * The backend accepts any of the three grounds from any port, so every port
 * exposes the same ground list here. "closed" is set statically from the known
 * western Gulf of Maine seasonal closure window (1 Feb–30 Apr) which contains
 * Jeffreys Ledge; the live endpoint recomputes closed/closed_reason per ?time.
 */

const JEFFREYS_CLOSED: Pick<Ground, 'closed' | 'closed_reason' | 'closed_from' | 'closed_to'> = {
  closed: true,
  closed_reason: 'Western Gulf of Maine Seasonal Closure',
  closed_from: '2026-02-01T00:00:00Z',
  closed_to: '2026-04-30T23:59:59Z',
};

function grounds(whaleSeasonActive: boolean): Ground[] {
  return [
    { id: 'stellwagen_bank', name: 'Stellwagen Bank', lon: -70.25, lat: 42.35 },
    {
      id: 'jeffreys_ledge',
      name: 'Jeffreys Ledge',
      lon: -70.25,
      lat: 42.9,
      ...(whaleSeasonActive ? JEFFREYS_CLOSED : { closed: false }),
    },
    { id: 'cape_cod_bay', name: 'Cape Cod Bay', lon: -70.35, lat: 41.9 },
  ];
}

/**
 * Build the bundled port list. `atIso` lets the fallback mark Jeffreys Ledge
 * closed only when the queried instant is inside the closure window, matching
 * how the live endpoint would answer ?time=.
 */
export function bundledPorts(atIso?: string): Port[] {
  const t = atIso ? new Date(atIso).getTime() : Date.now();
  const from = new Date(JEFFREYS_CLOSED.closed_from!).getTime();
  const to = new Date(JEFFREYS_CLOSED.closed_to!).getTime();
  const whaleSeasonActive = !isNaN(t) && t >= from && t <= to;
  const g = grounds(whaleSeasonActive);
  const ports: Array<Omit<Port, 'grounds'>> = [
    { id: 'gloucester', name: 'Gloucester', lon: -70.625, lat: 42.575 },
    { id: 'boston', name: 'Boston', lon: -70.875, lat: 42.425 },
    { id: 'plymouth', name: 'Plymouth', lon: -70.625, lat: 42.025 },
    { id: 'provincetown', name: 'Provincetown', lon: -70.18, lat: 42.05 },
    { id: 'new_bedford', name: 'New Bedford', lon: -70.912, lat: 41.63 },
  ];
  return ports.map((p) => ({ ...p, grounds: g.map((x) => ({ ...x })) }));
}
