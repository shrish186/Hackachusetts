import { Suspense, lazy, useState } from 'react';
import { TopBar } from '@/components/TopBar';
import { LeftRail } from '@/components/LeftRail';
import { TimeSlider } from '@/components/TimeSlider';
import { LayerPanel } from '@/components/LayerPanel';
import { CaptainPanel } from '@/captain/CaptainPanel';
import { DataSourcesModal } from '@/components/DataSourcesModal';
import { IntroCard } from '@/components/IntroCard';
import { OfflineBanner } from '@/components/OfflineBanner';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { MapUnavailable } from '@/map/MapUnavailable';
import { useAppState } from '@/state/AppState';
import { useMeta } from '@/hooks/useLayerData';
import { useRoute } from '@/lib/router';
import type { RoutePlan } from '@/api/types';

// About page is a lazy client route (item 5).
const AboutPage = lazy(() =>
  import('@/about/AboutPage').then((m) => ({ default: m.AboutPage })),
);

// Code-split the heavy map (MapLibre + deck.gl) and the Manager panel so the
// first paint on mobile is fast (task 12).
const MapView = lazy(() => import('@/map/MapView').then((m) => ({ default: m.MapView })));
const ManagerPanel = lazy(() =>
  import('@/manager/ManagerPanel').then((m) => ({ default: m.ManagerPanel })),
);

/**
 * The left column scrolls within the space between the top (1rem) and the
 * bottom time slider (~8rem), with extra bottom padding, so the header stack
 * and planner results are never hidden behind the timeline (tasks 2 + 4).
 */
const PANEL_SCROLL = 'max-h-[calc(100dvh-9rem)] overflow-y-auto overscroll-contain pb-6';

export function App() {
  const route = useRoute();
  const { mode } = useAppState();
  const meta = useMeta();
  const [selectedRoute, setSelectedRoute] = useState<RoutePlan | null>(null);
  const [sourcesOpen, setSourcesOpen] = useState(false);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [mapError, setMapError] = useState<string | null>(null);

  // Client-side route: /about renders the evidence page (item 5).
  if (route.replace(/\/$/, '') === '/about') {
    return (
      <ErrorBoundary fallback={<AboutFallback />}>
        <Suspense fallback={<div className="min-h-dvh bg-abyss" />}>
          <AboutPage />
        </Suspense>
      </ErrorBoundary>
    );
  }

  const panel =
    mode === 'captain' ? (
      <CaptainPanel onSelectedRoute={setSelectedRoute} />
    ) : (
      <ErrorBoundary fallback={<ManagerUnavailable />}>
        <Suspense fallback={<PanelLoading />}>
          <ManagerPanel />
        </Suspense>
      </ErrorBoundary>
    );

  return (
    <div className="relative h-dvh w-full overflow-hidden">
      {/* Full-screen dark ocean map (lazy). Map crashes fall back, planner stays. */}
      <ErrorBoundary fallback={<MapUnavailable detail={mapError ?? undefined} />}>
        <Suspense fallback={<div className="absolute inset-0 bg-abyss" />}>
          {mapError ? (
            <MapUnavailable detail={mapError} />
          ) : (
            <MapView
              routes={mode === 'captain' && selectedRoute ? [selectedRoute] : []}
              onError={setMapError}
            />
          )}
        </Suspense>
      </ErrorBoundary>

      {/* Top-right: mode toggle + data badge */}
      <TopBar demoMode={meta?.demo_mode ?? true} />

      {/*
        Left column (item 2): a single vertical flex stack — header rail,
        cold-start/offline banner, then the planner — so the replay banner can
        never overlap the "Plan a trip" title. The whole column scrolls as one.
        Desktop/tablet only; phones use the bottom sheet below.
      */}
      <div className="pointer-events-none absolute left-3 top-3 z-10 hidden sm:left-4 sm:top-4 sm:block">
        <div className={`flex flex-col gap-2 ${PANEL_SCROLL}`}>
          <div className="pointer-events-auto">
            <LeftRail
              dataTimestamp={meta?.data_timestamp ?? null}
              onOpenSources={() => setSourcesOpen(true)}
            />
          </div>
          <div className="pointer-events-auto">
            <OfflineBanner />
          </div>
          {panel}
        </div>
      </div>

      {/* Phone: compact header stack (rail + banner) top-left */}
      <div className="pointer-events-none absolute left-3 top-3 z-10 flex max-w-[82vw] flex-col gap-2 sm:hidden">
        <div className="pointer-events-auto">
          <LeftRail
            dataTimestamp={meta?.data_timestamp ?? null}
            onOpenSources={() => setSourcesOpen(true)}
          />
        </div>
        <div className="pointer-events-auto">
          <OfflineBanner />
        </div>
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
          <div className="pointer-events-auto absolute inset-x-0 bottom-0 z-30 max-h-[85dvh] overflow-y-auto overscroll-contain rounded-t-2xl border-t border-depth bg-deep/95 p-3 pb-8 shadow-2xl backdrop-blur">
            <div className="relative mb-2 flex items-center justify-center">
              <div className="h-1 w-10 rounded-full bg-mist/40" />
              <button
                onClick={() => setSheetOpen(false)}
                aria-label="Close panel"
                className="absolute right-1 flex h-9 w-9 items-center justify-center rounded-full text-mist hover:text-foam focus-visible:ring-2 focus-visible:ring-surf"
              >
                ✕
              </button>
            </div>
            {panel}
          </div>
        )}
      </div>

      {/* Right: layer toggles + legend, below the mode toggle (hidden on phones) */}
      <div className="pointer-events-none absolute right-3 top-28 z-10 hidden sm:right-4 sm:top-28 md:block">
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

function PanelLoading() {
  return (
    <aside className="pointer-events-auto w-80 max-w-[88vw] rounded-2xl border border-depth bg-deep/85 p-4 backdrop-blur">
      <div className="space-y-2">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="h-4 w-full animate-pulse rounded bg-current/20" />
        ))}
      </div>
    </aside>
  );
}

function ManagerUnavailable() {
  return (
    <aside className="pointer-events-auto w-80 max-w-[88vw] rounded-2xl border border-depth bg-deep/85 p-4 text-sm text-mist backdrop-blur">
      The simulator hit an error. Reload to try again — the trip planner still
      works.
    </aside>
  );
}

function AboutFallback() {
  return (
    <div className="min-h-dvh bg-abyss p-8 text-foam">
      <p className="text-sm text-mist">Could not load the About page.</p>
      <a href="/" className="mt-2 inline-block text-surf hover:underline">
        ← Back to the map
      </a>
    </div>
  );
}
