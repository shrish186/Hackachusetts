import { useEffect, useRef, useState } from 'react';
import {
  Map as MapLibreMap,
  NavigationControl,
  ScaleControl,
  type IControl,
} from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { MapboxOverlay } from '@deck.gl/mapbox';
import type { Zone, RiskCell, RoutePlan } from '@/api/types';
import { STUDY_AREA } from '@/config/studyArea';
import { DARK_OCEAN_STYLE } from './basemap';
import { buildDeckLayers } from './layers';
import { configureMapLibreWorker } from './worker';
import { useAppState } from '@/state/AppState';
import {
  useConditions,
  useRisk,
  useSightings,
  useZones,
} from '@/hooks/useLayerData';
import { sliceToIso } from '@/lib/time';
import { ZonePopup } from '@/components/ZonePopup';
import { RiskTooltip } from '@/components/RiskTooltip';

interface MapViewProps {
  /** Optional routes to draw (Captain mode). */
  routes?: RoutePlan[];
  /** Called if the map/WebGL/worker fails to initialise. */
  onError?: (message: string) => void;
}

export function MapView({ routes, onError }: MapViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const overlayRef = useRef<MapboxOverlay | null>(null);

  const { sliceIndex, speedKn, layers, drawing, drawnPolygon, setDrawnPolygon } =
    useAppState();
  const timeIso = sliceToIso(sliceIndex);

  // Keep the latest draw state in refs so the stable map click handler can read
  // it without re-binding on every change.
  const drawingRef = useRef(drawing);
  drawingRef.current = drawing;

  const zones = useZones(timeIso);
  const sightings = useSightings();
  const conditions = useConditions(timeIso, layers.conditions);
  const risk = useRisk(timeIso, speedKn, layers.risk);

  const [selectedZone, setSelectedZone] = useState<Zone | null>(null);
  const [hoverRisk, setHoverRisk] = useState<RiskCell | null>(null);
  const [cursor, setCursor] = useState<{ x: number; y: number } | null>(null);
  // Only render deck.gl layers once the map is loaded AND has a valid size.
  const [mapReady, setMapReady] = useState(false);

  // Initialize map once.
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    let map: MapLibreMap;
    try {
      configureMapLibreWorker();
      map = new MapLibreMap({
        container: containerRef.current,
        style: DARK_OCEAN_STYLE,
        center: [STUDY_AREA.center.lon, STUDY_AREA.center.lat],
        zoom: STUDY_AREA.zoom,
        minZoom: STUDY_AREA.minZoom,
        maxZoom: STUDY_AREA.maxZoom,
        attributionControl: { compact: true },
      });
    } catch (err) {
      // WebGL unavailable or MapLibre failed to construct.
      onError?.(err instanceof Error ? err.message : 'Map failed to initialise');
      return;
    }

    map.addControl(new NavigationControl({ showCompass: false }), 'top-right');
    map.addControl(new ScaleControl({ unit: 'nautical' }), 'bottom-left');

    // Surface async GL/worker errors (e.g. worker failed to load) to the UI.
    map.on('error', (e) => {
      const msg = (e && e.error && e.error.message) || '';
      if (/webgl|worker|context/i.test(msg)) onError?.(msg);
    });

    // Attach the deck.gl overlay only AFTER the style has loaded and the canvas
    // has a real size. Adding it earlier lets deck render against an unsized
    // viewport and throw "Cannot read properties of undefined (reading
    // 'height')". We also wait one resize/idle tick to be safe.
    map.on('load', () => {
      const c = map.getCanvas();
      if (!c || c.width === 0 || c.height === 0) return;
      map.resize(); // ensure the GL viewport matches the container
      if (!overlayRef.current && mapRef.current) {
        // Overlaid (non-interleaved) mode: deck renders in its own canvas and
        // derives its viewport from the map's move events, so it never reads
        // MapLibre's transform mid-initialisation (the source of the deck.gl
        // "reading 'height'" crash). Our data layers sit above the basemap
        // regardless, so z-ordering is unaffected.
        const overlay = new MapboxOverlay({ interleaved: false, layers: [] });
        map.addControl(overlay as unknown as IControl);
        overlayRef.current = overlay;
      }
      setMapReady(true);
    });

    // Polygon draw tool: click adds a vertex while draw mode is on.
    map.on('click', (e) => {
      if (!drawingRef.current) return;
      const v: [number, number] = [e.lngLat.lng, e.lngLat.lat];
      setDrawnPolygon((prev) => [...prev, v]);
    });

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
      overlayRef.current = null;
      setMapReady(false);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Keep the map sized to its container. MapLibre can initialise before the
  // container has its final height (we saw a 1440x300 canvas), leaving the map
  // a thin strip. A ResizeObserver calls map.resize() whenever the box changes.
  useEffect(() => {
    const el = containerRef.current;
    if (!el || typeof ResizeObserver === 'undefined') return;
    const ro = new ResizeObserver(() => mapRef.current?.resize());
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // Reflect draw mode in the cursor.
  useEffect(() => {
    const canvas = mapRef.current?.getCanvas();
    if (canvas) canvas.style.cursor = drawing ? 'crosshair' : '';
  }, [drawing]);

  // Track cursor for tooltips.
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const onMove = (e: MouseEvent) => setCursor({ x: e.clientX, y: e.clientY });
    el.addEventListener('mousemove', onMove);
    return () => el.removeEventListener('mousemove', onMove);
  }, []);

  // Rebuild deck layers when data/toggles change — but only once the map exists
  // and has a valid size (task 1: guard deck.gl so it never reads height of
  // undefined).
  useEffect(() => {
    if (!mapReady || !overlayRef.current) return;
    overlayRef.current.setProps({
      layers: buildDeckLayers({
        timeIso,
        zones,
        sightings,
        conditions,
        risk,
        show: layers,
        routeWaypoints: routes?.map((r) => r.waypoints),
        drawnPolygon,
        onZoneClick: setSelectedZone,
        onRiskHover: setHoverRisk,
      }),
    });
  }, [mapReady, timeIso, zones, sightings, conditions, risk, layers, routes, drawnPolygon]);

  return (
    <div className="absolute inset-0">
      {/*
        The container must size itself even though MapLibre forces
        `position: relative` on it (which cancels `inset-0`). Use explicit
        h-full/w-full against the absolutely-positioned full-size wrapper.
      */}
      <div ref={containerRef} className="h-full w-full" />
      {hoverRisk && cursor && <RiskTooltip cell={hoverRisk} x={cursor.x} y={cursor.y} />}
      {selectedZone && (
        <ZonePopup
          zone={selectedZone}
          timeIso={timeIso}
          onClose={() => setSelectedZone(null)}
        />
      )}
    </div>
  );
}
