import { GeoJsonLayer, ScatterplotLayer, GridCellLayer, PolygonLayer } from '@deck.gl/layers';
import type { Layer, PickingInfo } from '@deck.gl/core';
import type { Conditions, RiskCell, Sighting, Zone } from '@/api/types';
import { STUDY_AREA } from '@/config/studyArea';
import { ZONE_COLORS, isZoneActive } from '@/lib/zones';

type RGBA = [number, number, number, number];

function hexToRgb(hex: string): [number, number, number] {
  const n = parseInt(hex.replace('#', ''), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

/**
 * Smooth whale-risk heatmap ramp (item 3): transparent → amber → red.
 * Alpha is driven by the layer opacity; here we vary it slightly with risk so
 * near-zero cells fade out and high-risk cells read solid.
 * Stops: 0 = clear deep teal, 0.5 = amber (#f2994a), 1 = red (#e5544b).
 */
const AMBER: [number, number, number] = [242, 153, 74];
const RED: [number, number, number] = [229, 84, 75];
const LOW: [number, number, number] = [57, 183, 214]; // surf teal, nearly transparent

function riskColor(risk: number): RGBA {
  const v = Math.max(0, Math.min(1, risk));
  let rgb: [number, number, number];
  if (v < 0.5) {
    const t = v / 0.5;
    rgb = [lerp(LOW[0], AMBER[0], t), lerp(LOW[1], AMBER[1], t), lerp(LOW[2], AMBER[2], t)];
  } else {
    const t = (v - 0.5) / 0.5;
    rgb = [lerp(AMBER[0], RED[0], t), lerp(AMBER[1], RED[1], t), lerp(AMBER[2], RED[2], t)];
  }
  // Fade the lowest values toward transparent so the ramp reads 0→1.
  const a = Math.round(255 * (0.25 + 0.75 * v));
  return [Math.round(rgb[0]), Math.round(rgb[1]), Math.round(rgb[2]), a];
}

export interface LayerBuildArgs {
  timeIso: string;
  zones: Zone[];
  sightings: Sighting[];
  conditions: Conditions[];
  risk: RiskCell[];
  show: { conditions: boolean; zones: boolean; risk: boolean; sightings: boolean };
  routeWaypoints?: Array<[number, number]>[];
  /** Candidate-zone polygon vertices being drawn in Manager mode. */
  drawnPolygon?: Array<[number, number]>;
  onZoneClick?: (zone: Zone) => void;
  onRiskHover?: (cell: RiskCell | null) => void;
}

export function buildDeckLayers(args: LayerBuildArgs): Layer[] {
  const { timeIso, zones, sightings, conditions, risk, show } = args;
  const cell = STUDY_AREA.cellDeg;
  const layers: Layer[] = [];

  // --- Risk heatmap (item 3) ---
  // Draw each cell as a gapless filled square in lon/lat (no stroke), sized to
  // the 0.05° grid with a tiny overlap so adjacent cells never leave the
  // 1px row gaps that made GridCellLayer look like horizontal stripes.
  if (show.risk && risk.length) {
    const half = cell / 2;
    const pad = cell * 0.02; // ~0.5px overlap at demo zoom; hides seams
    layers.push(
      new PolygonLayer<RiskCell>({
        id: 'risk-grid',
        data: risk,
        getPolygon: (d) => {
          const w = d.lon - half - pad;
          const e = d.lon + half + pad;
          const s = d.lat - half - pad;
          const n = d.lat + half + pad;
          return [
            [w, s],
            [e, s],
            [e, n],
            [w, n],
            [w, s],
          ];
        },
        getFillColor: (d) => riskColor(d.risk),
        stroked: false,
        filled: true,
        opacity: 0.55,
        pickable: true,
        onHover: (info: PickingInfo<RiskCell>) =>
          args.onRiskHover?.(info.object ?? null),
      }),
    );
  }

  // --- Conditions (wave height) heatmap ---
  if (show.conditions && conditions.length) {
    const maxWave = 4;
    layers.push(
      new GridCellLayer<Conditions>({
        id: 'conditions-grid',
        data: conditions,
        cellSize: cell * 111000 * 0.9,
        // conditions carry only cell_id; derive position from the risk grid is
        // not reliable, so skip when positions unknown. Here we encode lon/lat
        // on the mock; for the real API this layer reads cell centroids.
        getPosition: (d) => conditionsPos(d),
        getFillColor: (d) => {
          const t = Math.min(1, d.wave_m / maxWave);
          return [40, Math.round(160 - 120 * t), Math.round(200 - 80 * t), 90];
        },
        pickable: false,
      }),
    );
  }

  // --- Zones (polygons) ---
  if (show.zones && zones.length) {
    const features: GeoJSON.Feature[] = zones.map((z) => ({
      type: 'Feature',
      geometry: z.geometry as GeoJSON.Geometry,
      properties: z as unknown as GeoJSON.GeoJsonProperties,
    }));
    const collection: GeoJSON.FeatureCollection = {
      type: 'FeatureCollection',
      features,
    };
    layers.push(
      new GeoJsonLayer({
        id: 'zones',
        data: collection,
        stroked: true,
        filled: true,
        getLineWidth: 2,
        lineWidthMinPixels: 1.5,
        getFillColor: (f: GeoJSON.Feature) => {
          const z = f.properties as unknown as Zone;
          const [r, g, b] = hexToRgb(ZONE_COLORS[z.kind]);
          const active = isZoneActive(z, timeIso);
          return [r, g, b, active ? 55 : 15] as RGBA;
        },
        getLineColor: (f: GeoJSON.Feature) => {
          const z = f.properties as unknown as Zone;
          const [r, g, b] = hexToRgb(ZONE_COLORS[z.kind]);
          const active = isZoneActive(z, timeIso);
          return [r, g, b, active ? 230 : 80] as RGBA;
        },
        pickable: true,
        onClick: (info: PickingInfo) => {
          const z = (info.object as GeoJSON.Feature | null)?.properties as
            | Zone
            | undefined;
          if (z) args.onZoneClick?.(z);
        },
        updateTriggers: {
          getFillColor: [timeIso],
          getLineColor: [timeIso],
        },
      }),
    );
  }

  // --- Sightings ---
  if (show.sightings && sightings.length) {
    layers.push(
      new ScatterplotLayer<Sighting>({
        id: 'sightings',
        data: sightings,
        getPosition: (d) => [d.lon, d.lat],
        getRadius: (d) => 1200 + d.count * 900,
        radiusMinPixels: 4,
        radiusMaxPixels: 22,
        getFillColor: [233, 244, 249, 160],
        getLineColor: [57, 183, 214, 255],
        lineWidthMinPixels: 1.5,
        stroked: true,
        pickable: true,
      }),
    );
  }

  // --- Route polylines (Captain mode) ---
  if (args.routeWaypoints?.length) {
    const palette: RGBA[] = [
      [57, 183, 214, 255],
      [63, 174, 143, 255],
      [242, 153, 74, 255],
    ];
    args.routeWaypoints.forEach((wp, i) => {
      layers.push(
        new GeoJsonLayer({
          id: `route-${i}`,
          data: {
            type: 'Feature',
            geometry: { type: 'LineString', coordinates: wp },
            properties: {},
          } as GeoJSON.Feature,
          stroked: true,
          filled: false,
          getLineWidth: 3,
          lineWidthMinPixels: 3,
          getLineColor: palette[i % palette.length],
        }),
      );
    });
  }

  // --- Drawn candidate zone (Manager mode) ---
  const poly = args.drawnPolygon;
  if (poly && poly.length > 0) {
    // Closed ring when we have 3+ vertices; otherwise show the open line.
    if (poly.length >= 3) {
      layers.push(
        new GeoJsonLayer({
          id: 'draw-polygon',
          data: {
            type: 'Feature',
            geometry: { type: 'Polygon', coordinates: [[...poly, poly[0]]] },
            properties: {},
          } as GeoJSON.Feature,
          stroked: true,
          filled: true,
          getFillColor: [57, 183, 214, 50],
          getLineColor: [57, 183, 214, 230],
          getLineWidth: 2,
          lineWidthMinPixels: 2,
        }),
      );
    } else if (poly.length === 2) {
      layers.push(
        new GeoJsonLayer({
          id: 'draw-line',
          data: {
            type: 'Feature',
            geometry: { type: 'LineString', coordinates: poly },
            properties: {},
          } as GeoJSON.Feature,
          stroked: true,
          filled: false,
          getLineColor: [57, 183, 214, 230],
          getLineWidth: 2,
          lineWidthMinPixels: 2,
        }),
      );
    }
    // Vertex dots.
    layers.push(
      new ScatterplotLayer<[number, number]>({
        id: 'draw-vertices',
        data: poly,
        getPosition: (d) => d,
        getRadius: 5,
        radiusMinPixels: 4,
        radiusMaxPixels: 7,
        getFillColor: [230, 244, 249, 255],
        getLineColor: [57, 183, 214, 255],
        lineWidthMinPixels: 2,
        stroked: true,
      }),
    );
  }

  return layers;
}

/** Mock conditions include lon/lat when generated locally; fall back safely. */
function conditionsPos(d: Conditions): [number, number] {
  const maybe = d as unknown as { lon?: number; lat?: number };
  if (typeof maybe.lon === 'number' && typeof maybe.lat === 'number') {
    return [maybe.lon, maybe.lat];
  }
  // Derive from cell_id "ix_iy" against the study grid origin.
  const [ix, iy] = d.cell_id.split('_').map(Number);
  const [minLon, minLat] = STUDY_AREA.bbox;
  return [minLon + ix * STUDY_AREA.cellDeg, minLat + iy * STUDY_AREA.cellDeg];
}
