import type { StyleSpecification } from 'maplibre-gl';

/**
 * A free, no-API-key dark basemap style for MapLibre.
 *
 * Uses CARTO's public "dark matter (no labels)" raster tiles plus a separate
 * labels layer. CARTO basemaps are free to use with attribution and require no
 * token, which keeps the demo key-free (no secrets, per data-and-safety
 * steering). Swap `tiles` for any other XYZ endpoint if needed.
 */
// NOTE: no `{r}` retina placeholder — MapLibre leaves it literal (URL-encoded
// as %7Br%7D) with 256px tiles, which returns blank images. Use plain tiles.
const CARTO_DARK_NOLABELS = [
  'https://a.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}.png',
  'https://b.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}.png',
  'https://c.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}.png',
  'https://d.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}.png',
];

const CARTO_DARK_LABELS = [
  'https://a.basemaps.cartocdn.com/dark_only_labels/{z}/{x}/{y}.png',
  'https://b.basemaps.cartocdn.com/dark_only_labels/{z}/{x}/{y}.png',
  'https://c.basemaps.cartocdn.com/dark_only_labels/{z}/{x}/{y}.png',
  'https://d.basemaps.cartocdn.com/dark_only_labels/{z}/{x}/{y}.png',
];

const ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions" target="_blank" rel="noreferrer">CARTO</a>';

export const DARK_OCEAN_STYLE: StyleSpecification = {
  version: 8,
  // Oceans read as deep teal between tiles / at low zoom.
  sources: {
    'carto-dark': {
      type: 'raster',
      tiles: CARTO_DARK_NOLABELS,
      tileSize: 256,
      attribution: ATTRIBUTION,
    },
    'carto-labels': {
      type: 'raster',
      tiles: CARTO_DARK_LABELS,
      tileSize: 256,
    },
  },
  layers: [
    {
      id: 'ocean-bg',
      type: 'background',
      paint: { 'background-color': '#04121f' },
    },
    {
      id: 'carto-dark',
      type: 'raster',
      source: 'carto-dark',
      paint: {
        // Tint the land/relief toward the ocean theme and knock it back so
        // the data layers pop.
        'raster-opacity': 0.9,
        'raster-saturation': -0.2,
        'raster-contrast': 0.05,
      },
    },
    {
      id: 'carto-labels',
      type: 'raster',
      source: 'carto-labels',
      paint: { 'raster-opacity': 0.85 },
    },
  ],
};
