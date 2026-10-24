import { useState } from 'react';
import { MapView } from '@/map/MapView';
import { TopBar } from '@/components/TopBar';
import { TimeSlider } from '@/components/TimeSlider';
import { LayerPanel } from '@/components/LayerPanel';
import { CaptainPanel } from '@/captain/CaptainPanel';
import { ManagerPanel } from '@/manager/ManagerPanel';
import { DataSourcesModal } from '@/components/DataSourcesModal';
import { IntroCard } from '@/components/IntroCard';
import { useAppState } from '@/state/AppState';
import { useMeta } from '@/hooks/useLayerData';
import type { RoutePlan } from '@/api/types';

export function App() {
  const { mode } = useAppState();
  const meta = useMeta();
  const [selectedRoute, setSelectedRoute] = useState<RoutePlan | null>(null);
  const [sourcesOpen, setSourcesOpen] = useState(false);
  const [sheetOpen, setSheetOpen] = useState(false);

  return (
    <div className="relative h-full w-full overflow-hidden">
      {/* Full-screen dark ocean map. Captain mode draws the selected plan. */}
      <MapView
        routes={mode === 'captain' && selectedRoute ? [selectedRoute] : []}
      />

      {/* Top bar: brand, data timestamp + sources, mode toggle, demo badge */}
      <TopBar
        demoMode={meta?.demo_mode ?? true}
        dataTimestamp={meta?.data_timestamp ?? null}
        onOpenSources={() => setSourcesOpen(true)}
      />

      {/*
        Mode-specific panel.
        - Desktop/tablet (sm+): docked top-left.
        - Phone (<sm): a bottom sheet toggled by a floating button, so the map
          stays usable (task 7).
      */}
      <div className="pointer-events-none absolute left-3 top-28 z-10 hidden sm:top-32 sm:left-4 sm:block">
        {mode === 'captain' ? (
          <CaptainPanel onSelectedRoute={setSelectedRoute} />
        ) : (
          <ManagerPanel />
        )}
      </div>

      {/* Phone bottom sheet */}
      <div className="sm:hidden">
        {!sheetOpen && (
          <button
            onClick={() => setSheetOpen(true)}
            className="pointer-events-auto absolute bottom-28 left-1/2 z-20 min-h-11 -translate-x-1/2 rounded-full bg-tide px-6 font-semibold text-foam shadow-lg focus-visible:ring-2 focus-visible:ring-surf"
          >
            {mode === 'captain' ? 'Plan a trip' : 'Simulator'}
          </button>
        )}
        {sheetOpen && (
          <div className="pointer-events-auto absolute inset-x-0 bottom-0 z-30 max-h-[82vh] overflow-y-auto rounded-t-2xl border-t border-depth bg-deep/95 p-3 pb-6 shadow-2xl backdrop-blur">
            <div className="mb-2 flex items-center justify-between">
              <div className="mx-auto h-1 w-10 rounded-full bg-mist/40" />
              <button
                onClick={() => setSheetOpen(false)}
                aria-label="Close panel"
                className="absolute right-3 flex h-9 w-9 items-center justify-center rounded-full text-mist hover:text-foam focus-visible:ring-2 focus-visible:ring-surf"
              >
                ✕
              </button>
            </div>
            {mode === 'captain' ? (
              <CaptainPanel onSelectedRoute={setSelectedRoute} />
            ) : (
              <ManagerPanel />
            )}
          </div>
        )}
      </div>

      {/* Right: layer toggles + legend (hidden on narrow phones to keep the map clear) */}
      <div className="pointer-events-none absolute right-3 top-28 z-10 hidden sm:top-36 sm:right-4 md:block">
        <LayerPanel />
      </div>

      {/* Bottom time slider */}
      <TimeSlider />

      {/* First-visit intro + data sources modal */}
      <IntroCard />
      <DataSourcesModal open={sourcesOpen} onClose={() => setSourcesOpen(false)} />
    </div>
  );
}
