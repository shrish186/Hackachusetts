import {
  createContext,
  useContext,
  useMemo,
  useState,
  type Dispatch,
  type ReactNode,
  type SetStateAction,
} from 'react';
import type { Language } from '@/api/types';
import {
  REPLAY_WHALE_SEASON_ISO,
  defaultDeparture,
  isoToDatetimeLocal,
  isoToSlice,
  sliceToIso,
  toDatetimeLocalValue,
} from '@/lib/time';

export type Mode = 'captain' | 'manager';

export interface LayerToggles {
  conditions: boolean;
  zones: boolean;
  risk: boolean;
  sightings: boolean;
}

export interface AppState {
  mode: Mode;
  setMode: (m: Mode) => void;

  /** Time slider index into the demo slices (see lib/time.ts). */
  sliceIndex: number;
  setSliceIndex: Dispatch<SetStateAction<number>>;

  /** Planned vessel speed (kn) — drives the risk layer lethality term. */
  speedKn: number;
  setSpeedKn: Dispatch<SetStateAction<number>>;

  /** UI + plan-text language (requirements.md Req 7). */
  language: Language;
  setLanguage: Dispatch<SetStateAction<Language>>;

  /**
   * "Replay whale season" toggle. When true, all layer fetches use the
   * whale-season instant and departure defaults to that date (item 1).
   */
  replay: boolean;
  setReplay: Dispatch<SetStateAction<boolean>>;

  /**
   * Shared departure as a datetime-local value (local wall-clock). The time
   * slider and the Captain departure field both read/write this, so they stay
   * in sync (item 3).
   */
  departure: string;
  setDeparture: Dispatch<SetStateAction<string>>;

  /**
   * UTC instant the map layers should be fetched at: the whale-season instant
   * when replay is on, otherwise the current departure/slider instant.
   */
  layerTimeIso: string;

  /** Manager draw tool: true while the user is placing polygon vertices. */
  drawing: boolean;
  setDrawing: Dispatch<SetStateAction<boolean>>;
  /** The candidate-zone polygon being drawn, as [lon, lat] vertices. */
  drawnPolygon: Array<[number, number]>;
  setDrawnPolygon: Dispatch<SetStateAction<Array<[number, number]>>>;

  layers: LayerToggles;
  toggleLayer: (key: keyof LayerToggles) => void;
}

const AppStateContext = createContext<AppState | null>(null);

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<Mode>('captain');
  const [speedKn, setSpeedKn] = useState(10);
  const [language, setLanguage] = useState<Language>('en');
  const [replay, setReplayState] = useState(false);
  // Departure (local wall-clock) is the single source of truth for time; the
  // slider derives from and writes to it (item 3).
  const [departure, setDeparture] = useState(() =>
    toDatetimeLocalValue(defaultDeparture()),
  );
  const [drawing, setDrawing] = useState(false);
  const [drawnPolygon, setDrawnPolygon] = useState<Array<[number, number]>>([]);
  const [layers, setLayers] = useState<LayerToggles>({
    conditions: false,
    zones: true,
    risk: true,
    sightings: true,
  });

  // Slice index is derived from the departure instant so the slider tracks it.
  const sliceIndex = useMemo(
    () => isoToSlice(new Date(departure).toISOString()),
    [departure],
  );

  // Layer fetch time: whale-season instant when replaying, else the departure.
  const layerTimeIso = useMemo(
    () => (replay ? REPLAY_WHALE_SEASON_ISO : new Date(departure).toISOString()),
    [replay, departure],
  );
  const setSliceIndex: Dispatch<SetStateAction<number>> = (next) => {
    const idx =
      typeof next === 'function' ? (next as (p: number) => number)(sliceIndex) : next;
    // Moving the slider sets the departure to that slice's local wall-clock.
    setDeparture(isoToDatetimeLocal(sliceToIso(idx)));
  };

  // Turning replay on/off snaps the departure (and therefore the slider).
  const setReplay: Dispatch<SetStateAction<boolean>> = (next) => {
    const on = typeof next === 'function' ? (next as (p: boolean) => boolean)(replay) : next;
    setReplayState(on);
    setDeparture(
      on
        ? isoToDatetimeLocal(REPLAY_WHALE_SEASON_ISO)
        : toDatetimeLocalValue(defaultDeparture()),
    );
  };

  const value = useMemo<AppState>(
    () => ({
      mode,
      setMode,
      sliceIndex,
      setSliceIndex,
      speedKn,
      setSpeedKn,
      language,
      setLanguage,
      replay,
      setReplay,
      departure,
      setDeparture,
      layerTimeIso,
      drawing,
      setDrawing,
      drawnPolygon,
      setDrawnPolygon,
      layers,
      toggleLayer: (key) =>
        setLayers((prev) => ({ ...prev, [key]: !prev[key] })),
    }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [mode, sliceIndex, layerTimeIso, speedKn, language, replay, departure, drawing, drawnPolygon, layers],
  );

  return (
    <AppStateContext.Provider value={value}>{children}</AppStateContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAppState(): AppState {
  const ctx = useContext(AppStateContext);
  if (!ctx) throw new Error('useAppState must be used within AppStateProvider');
  return ctx;
}
