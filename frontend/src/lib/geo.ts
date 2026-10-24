/** Geometry helpers for the Manager draw tool (item 5). */

/**
 * Approximate area of a lon/lat polygon in square nautical miles, using the
 * shoelace formula on a local equirectangular projection (good enough at this
 * scale for a human-readable "Area ~X nm²" chip).
 */
export function polygonAreaNm2(ring: Array<[number, number]>): number {
  if (ring.length < 3) return 0;
  // Reference latitude for the x-scale (longitude degrees shrink with cos lat).
  const lat0 = ring.reduce((a, p) => a + p[1], 0) / ring.length;
  const NM_PER_DEG_LAT = 60; // 1° latitude ≈ 60 nm
  const nmPerDegLon = 60 * Math.cos((lat0 * Math.PI) / 180);

  // Project to nm (x east, y north) relative to the first vertex.
  const pts = ring.map(([lon, lat]) => [
    (lon - ring[0][0]) * nmPerDegLon,
    (lat - ring[0][1]) * NM_PER_DEG_LAT,
  ]);
  let area = 0;
  for (let i = 0; i < pts.length; i++) {
    const [x1, y1] = pts[i];
    const [x2, y2] = pts[(i + 1) % pts.length];
    area += x1 * y2 - x2 * y1;
  }
  return Math.abs(area) / 2;
}
