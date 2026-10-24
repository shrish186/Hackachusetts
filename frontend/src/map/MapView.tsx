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
}

export function MapView({ routes }: MapViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const overlayRef = useRef<MapboxOverlay | null>(null);

  const { sliceIndex, speedKn, layers } = useAppState();
  const timeIso = sliceToIso(sliceIndex);

  const zones = useZones(timeIso);
  const sightings = useSightings();
  const conditions = useConditions(timeIso, layers.conditions);
  const risk = useRisk(timeIso, speedKn, layers.risk);

  const [selectedZone, setSelectedZone] = useState<Zone | null>(null);
  const [hoverRisk, setHoverRisk] = useState<RiskCell | null>(null);
  const [cursor, setCursor] = useState<{ x: number; y: number } | null>(null);

  // Initialize map once.
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = new MapLibreMap({
      container: containerRef.current,
      style: DARK_OCEAN_STYLE,
      center: [STUDY_AREA.center.lon, STUDY_AREA.center.lat],
      zoom: STUDY_AREA.zoom,
      minZoom: STUDY_AREA.minZoom,
      maxZoom: STUDY_AREA.maxZoom,
      attributionControl: { compact: true },
    });
    map.addControl(new NavigationControl({ showCompass: false }), 'top-right');
    map.addControl(new ScaleControl({ unit: 'nautical' }), 'bottom-left');

    const overlay = new MapboxOverlay({ interleaved: true, layers: [] });
    map.addControl(overlay as unknown as IControl);

    mapRef.current = map;
    overlayRef.current = overlay;

    return () => {
      map.remove();
      mapRef.current = null;
      overlayRef.current = null;
    };
  }, []);

  // Track cursor for tooltips.
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const onMove = (e: MouseEvent) => setCursor({ x: e.clientX, y: e.clientY });
    el.addEventListener('mousemove', onMove);
    return () => el.removeEventListener('mousemove', onMove);
  }, []);

  // Rebuild deck layers when data/toggles change.
  useEffect(() => {
    overlayRef.current?.setProps({
      layers: buildDeckLayers({
        timeIso,
        zones,
        sightings,
        conditions,
        risk,
        show: layers,
        routeWaypoints: routes?.map((r) => r.waypoints),
        onZoneClick: setSelectedZone,
        onRiskHover: setHoverRisk,
      }),
    });
  }, [timeIso, zones, sightings, conditions, risk, layers, routes]);

  return (
    <div className="absolute inset-0">
      <div ref={containerRef} className="absolute inset-0" />
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
