/**
 * Shared data types for Fathom.
 *
 * These mirror the pydantic models in design.md §4 and the API responses in
 * design.md §9. Keep them in sync with /backend/app/models and the example
 * JSON in /data/snapshots/examples.
 */

/** A GeoJSON geometry (we only use Polygon/MultiPolygon in practice). */
export type GeoJSONGeometry = {
  type: string;
  coordinates: unknown;
};

/** One grid square of the study area. */
export interface Cell {
  id: string; // "ix_iy"
  lon: number;
  lat: number;
  is_land: boolean;
}

export type ZoneKind =
  | 'whale_sma'
  | 'slow_zone'
  | 'fishing_closure'
  | 'wind_lease'
  | 'wind_construction';

/** A regulatory / protection polygon. */
export interface Zone {
  id: string;
  name: string;
  kind: ZoneKind;
  geometry: GeoJSONGeometry;
  active_from: string | null; // ISO datetime (UTC)
  active_to: string | null; // ISO datetime (UTC)
  speed_limit_kn: number | null;
  prohibited: boolean;
  source_url: string;
  source_updated: string; // ISO datetime (UTC)
  /** Present on synthetic/hand-digitized data. See data-and-safety steering. */
  synthetic?: boolean;
}

/** A whale sighting (public aggregate or synthetic seed). */
export interface Sighting {
  lon: number;
  lat: number;
  observed_at: string; // ISO datetime (UTC)
  count: number;
  source: string;
}

/** Sea-state / weather conditions for one cell at one time. */
export interface Conditions {
  cell_id: string;
  time: string; // ISO datetime (UTC)
  wave_m: number;
  wind_kn: number;
  sst_c: number | null;
  source: string;
  fetched_at: string; // ISO datetime (UTC)
}

/** A single risk-grid cell returned by GET /api/layers/risk. */
export interface RiskCell {
  cell_id: string;
  lon: number;
  lat: number;
  risk: number; // 0..1
  /** Top contributing factors per cell (design.md §7 get_whale_risk). */
  factors: {
    presence: number;
    recency: number;
    lethality: number;
  };
}

export type VesselType = 'small_boat' | 'mid_trawler' | 'scalloper';
export type Language = 'en' | 'pt' | 'es';

/** Trip request submitted in Captain mode. */
export interface TripRequest {
  port: string;
  vessel: VesselType;
  cruise_kn: number;
  max_hours: number;
  depart_window: [string, string]; // [from, to] ISO datetimes
  target_ground: string | null;
  risk_pref: number; // 0 = fastest, 1 = safest
  language: Language;
}

/** A citation attached to any agent factual claim. */
export interface Citation {
  tool_call_id: string;
  tool: string;
  claim: string;
  source_url: string | null;
  /** Human source label shown when source_url is null (e.g. "bundled demo data (synthetic)"). */
  source_label?: string;
}

/** A weather window for the planned departure (design.md §10 plan "why"). */
export interface WeatherWindow {
  /** ISO datetime (UTC) the window opens / closes. */
  from: string;
  to: string;
  max_wave_m: number;
  max_wind_kn: number;
  /** Short human summary, e.g. "building seas after 3pm". */
  note: string;
}

/** One planned route alternative. */
export interface RoutePlan {
  /** Optional short label for the plan, e.g. "Direct run". */
  name?: string;
  waypoints: Array<[number, number]>; // [lon, lat]
  eta_hours: number;
  fuel_est_l: number;
  zones_crossed: string[]; // zone ids
  max_wave_m: number;
  risk_exposure: number; // sum(risk * hours)
  effort_proxy: number; // estimate, NOT revenue
  citations: Citation[];
  /** Optional weather window for the "why" drawer. */
  weather_window?: WeatherWindow;
}

/** A single streamed agent step (design.md §7; requirements.md Req 4.5). */
export interface AgentEvent {
  id: string;
  /** The tool the agent is calling, e.g. "get_zones". */
  tool: string;
  /** Plain-language label shown in the live feed, e.g. "Checking zones…". */
  label: string;
  status: 'running' | 'done' | 'error';
  /** Optional one-line result summary once done. */
  detail?: string;
}

/** Metadata about data sources and demo mode. GET /api/meta/sources. */
export interface SourceMeta {
  layer: string;
  source_url: string | null;
  fetched_at: string | null;
  cached: boolean;
  synthetic: boolean;
}

export interface MetaResponse {
  demo_mode: boolean;
  sources: SourceMeta[];
  /** Latest common data timestamp to show in the timestamp strip. */
  data_timestamp: string;
}

/** A selectable scenario from GET /api/sim/scenarios (Manager mode). */
export interface ScenarioListItem {
  /** Stable scenario id (contract field: `id`). */
  scenario_id: string;
  /** Display name. */
  label: string;
  description?: string;
  synthetic?: boolean;
}

/** Scenario result from POST /api/sim/run (Manager mode). */
export interface ScenarioResult {
  scenario_id: string;
  label: string;
  delta_risk_pct: number;
  delta_hours_pct: number;
  delta_fuel_pct: number;
  delta_effort_access_pct: number;
  on_frontier: boolean;
  /** Plain-language summary in the user's language (already localized). */
  summary: string;
}

/** Bounding box [minLon, minLat, maxLon, maxLat]. */
export type BBox = [number, number, number, number];
