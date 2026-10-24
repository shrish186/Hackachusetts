import type { StyleSpecification } from 'maplibre-gl';

/**
 * A free, no-API-key dark basemap style for MapLibre.
 *
 * Uses the standard OpenStreetMap raster tiles — genuinely keyless and
 * CORS-enabled — and darkens/desaturates them with MapLibre raster paint to fit
 * the dark ocean theme. (CARTO's keyless raster tiles were discontinued in
 * Aug 2026 and now render an "API KEY REQUIRED" watermark, so they can't be
 * used token-free.)
 *
 * OSM tile usage policy: include attribution (below) and keep traffic modest —
 * fine for this demo. Swap `tiles` for any other keyless XYZ endpoint if needed.
 */
const OSM_TILES = [
  'https://a.tile.openstreetmap.org/{z}/{x}/{y}.png',
  'https://b.tile.openstreetmap.org/{z}/{x}/{y}.png',
  'https://c.tile.openstreetmap.org/{z}/{x}/{y}.png',
];

const ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a> contributors';

export const DARK_OCEAN_STYLE: StyleSpecification = {
  version: 8,
  // Oceans read as deep teal between tiles / at low zoom.
  sources: {
    osm: {
      type: 'raster',
      tiles: OSM_TILES,
      tileSize: 256,
      maxzoom: 19,
      attribution: ATTRIBUTION,
    },
  },
  layers: [
    {
      id: 'ocean-bg',
      type: 'background',
      paint: { 'background-color': '#04121f' },
    },
    {
      id: 'osm',
      type: 'raster',
      source: 'osm',
      paint: {
        // Darken + desaturate the light OSM tiles into the ocean theme so the
        // data layers (risk, zones, routes) still pop on top.
        'raster-opacity': 0.55,
        'raster-saturation': -0.6,
        'raster-brightness-max': 0.55,
        'raster-contrast': 0.1,
      },
    },
  ],
};
