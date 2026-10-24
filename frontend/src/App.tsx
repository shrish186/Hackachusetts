import { useState } from 'react';
import { MapView } from '@/map/MapView';
import { TopBar } from '@/components/TopBar';
import { TimeSlider } from '@/components/TimeSlider';
import { LayerPanel } from '@/components/LayerPanel';
import { CaptainPanel } from '@/captain/CaptainPanel';
import { ManagerPanel } from '@/manager/ManagerPanel';
import { useAppState } from '@/state/AppState';
import { useMeta } from '@/hooks/useLayerData';
import type { RoutePlan } from '@/api/types';

export function App() {
  const { mode } = useAppState();
  const meta = useMeta();
  const [selectedRoute, setSelectedRoute] = useState<RoutePlan | null>(null);

  return (
    <div className="relative h-full w-full overflow-hidden">
      {/* Full-screen dark ocean map. Captain mode draws the selected plan. */}
      <MapView
        routes={mode === 'captain' && selectedRoute ? [selectedRoute] : []}
      />

      {/* Top bar: brand, data timestamp, mode toggle, demo badge */}
      <TopBar demoMode={meta?.demo_mode ?? true} dataTimestamp={meta?.data_timestamp ?? null} />

      {/* Left: mode-specific panel */}
      <div className="pointer-events-none absolute left-3 top-28 z-10 sm:top-32 sm:left-4">
        {mode === 'captain' ? (
          <CaptainPanel onSelectedRoute={setSelectedRoute} />
        ) : (
          <ManagerPanel />
        )}
      </div>

      {/* Right: layer toggles + legend (hidden on narrow phones to keep the map clear) */}
      <div className="pointer-events-none absolute right-3 top-28 z-10 hidden sm:top-36 sm:right-4 md:block">
        <LayerPanel />
      </div>

      {/* Bottom time slider */}
      <TimeSlider />
    </div>
  );
}
