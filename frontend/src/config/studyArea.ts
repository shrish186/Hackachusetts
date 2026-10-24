import type { BBox } from '@/api/types';

/**
 * Study area: Massachusetts Bay, Cape Cod Bay, and the approaches
 * (design.md §4: roughly 41°N–43.5°N, 71°W–69°W). Grid is 0.05° per cell
 * (requirements.md glossary).
 */
export const STUDY_AREA = {
  /** [minLon, minLat, maxLon, maxLat] */
  bbox: [-71.0, 41.0, -69.0, 43.5] as BBox,
  cellDeg: 0.05,
  /** Map view centered on Massachusetts Bay. */
  center: { lon: -70.3, lat: 42.3 } as const,
  zoom: 7.6,
  minZoom: 6,
  maxZoom: 12,
} as const;
