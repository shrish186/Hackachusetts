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
  const [sliceIndex, setSliceIndex] = useState(6); // ~Sat afternoon
  const [speedKn, setSpeedKn] = useState(10);
  const [language, setLanguage] = useState<Language>('en');
  const [drawing, setDrawing] = useState(false);
  const [drawnPolygon, setDrawnPolygon] = useState<Array<[number, number]>>([]);
  const [layers, setLayers] = useState<LayerToggles>({
    conditions: false,
    zones: true,
    risk: true,
    sightings: true,
  });

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
      drawing,
      setDrawing,
      drawnPolygon,
      setDrawnPolygon,
      layers,
      toggleLayer: (key) =>
        setLayers((prev) => ({ ...prev, [key]: !prev[key] })),
    }),
    [mode, sliceIndex, speedKn, language, drawing, drawnPolygon, layers],
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
