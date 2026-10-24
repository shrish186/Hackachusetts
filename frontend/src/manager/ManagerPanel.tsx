import { useEffect, useRef, useState } from 'react';
import { api, ApiError } from '@/api/client';
import * as mock from '@/mocks';
import type { ScenarioListItem, ScenarioResult } from '@/api/types';
import { useAppState } from '@/state/AppState';
import { useConn } from '@/hooks/useConn';
import { t } from '@/lib/i18n';
import { TradeoffChart } from './TradeoffChart';

/**
 * Manager mode panel (tasks.md task 4 + task 9).
 *
 * - Polygon draw tool (vertices placed on the map; finish/clear here)
 * - Scenario list from GET /api/sim/scenarios
 * - Run button -> POST /api/sim/run (drawn polygon as candidate zone if any),
 *   with a progress state, 60 s client timeout, and a Cancel button
 *   (AbortController). Handles 429 / 504 with friendly messages and a retry.
 * - SVG trade-off chart with the efficient frontier highlighted
 * - Plain-language summary in the selected language
 * Falls back to realistic mock numbers (labeled demo) when offline.
 */
export function ManagerPanel() {
  const { language, drawing, setDrawing, drawnPolygon, setDrawnPolygon } = useAppState();
  const conn = useConn();
  const s = t(language);

  const [list, setList] = useState<ScenarioListItem[]>([]);
  const [results, setResults] = useState<ScenarioResult[]>([]);
  const [baselineAccessLost, setBaselineAccessLost] = useState<number | null>(null);
  const [baselineTrips, setBaselineTrips] = useState<number | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [loadingList, setLoadingList] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Load the selectable scenario list once.
  useEffect(() => {
    let alive = true;
    api.getScenarios().then((items) => {
      if (!alive) return;
      setList(items);
      setLoadingList(false);
    });
    return () => {
      alive = false;
    };
  }, []);

  // Cancel any in-flight run on unmount.
  useEffect(() => () => abortRef.current?.abort(), []);

  function applyResults(res: ScenarioResult[], accessLost: number | null, trips: number | null) {
    setResults(res);
    setBaselineAccessLost(accessLost);
    setBaselineTrips(trips);
    const firstFrontier = res.find((r) => r.on_frontier) ?? res[0];
    setSelectedId(firstFrontier?.scenario_id ?? null);
  }

  async function run() {
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    setRunning(true);
    setError(null);
    try {
      const res = await api.runScenario({
        polygon: drawnPolygon.length >= 3 ? drawnPolygon : undefined,
        scenarioId: 'seasonal_speed_limit',
        language,
        signal: ac.signal,
        timeoutMs: 60_000,
      });
      if (ac.signal.aborted) return;
      applyResults(res.results.length ? res.results : mock.scenarios, res.baselineAccessLost, res.baselineTrips);
    } catch (err) {
      if (ac.signal.aborted) return; // user cancelled; stay quiet
      // Friendly messages for the documented error codes; always recover with
      // sample numbers so the view is never empty.
      if (err instanceof ApiError && err.status === 429) setError(s.simBusy);
      else if (err instanceof ApiError && (err.status === 504)) setError(s.simSlow);
      else if (err instanceof DOMException && err.name === 'AbortError') setError(s.simTimeout);
      else setError(s.simError);
      // Mock numbers carry no real baseline access-lost count (do not hardcode).
      applyResults(mock.scenarios, null, null);
    } finally {
      if (!ac.signal.aborted) setRunning(false);
    }
  }

  function cancel() {
    abortRef.current?.abort();
    setRunning(false);
  }

  const selected = results.find((r) => r.scenario_id === selectedId) ?? null;

  return (
    <aside className="pointer-events-auto flex w-80 max-w-[88vw] flex-col gap-3 rounded-2xl border border-depth bg-deep/85 p-4 backdrop-blur">
      <h2 className="text-sm font-bold text-foam">{s.simTitle}</h2>
      <p className="text-xs leading-snug text-mist">{s.simIntro}</p>

      {/* Draw tool */}
      <div className="rounded-xl border border-depth bg-abyss/40 p-3">
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setDrawing((d) => !d)}
            aria-pressed={drawing}
            className={[
              'min-h-9 flex-1 rounded-lg px-3 text-xs font-semibold transition-colors focus-visible:ring-2 focus-visible:ring-surf',
              drawing ? 'bg-surf text-abyss' : 'bg-tide text-foam hover:bg-surf',
            ].join(' ')}
          >
            {drawing ? s.finishZone : s.drawZone}
          </button>
          <button
            onClick={() => {
              setDrawnPolygon([]);
              setDrawing(false);
            }}
            disabled={drawnPolygon.length === 0}
            className="min-h-9 rounded-lg border border-depth px-3 text-xs font-semibold text-mist transition-colors hover:text-foam disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-surf"
          >
            {s.clearZone}
          </button>
        </div>
        {drawing && <p className="mt-2 text-[11px] leading-snug text-surf">{s.drawHint}</p>}
        {drawnPolygon.length > 0 && (
          <p className="mt-2 text-[11px] text-mist">
            {drawnPolygon.length} {drawnPolygon.length === 1 ? 'vertex' : 'vertices'}
          </p>
        )}
      </div>

      {/* Scenario list */}
      <div>
        <h3 className="mb-1 text-[11px] font-bold uppercase tracking-wide text-mist">
          {s.scenarios}
        </h3>
        {loadingList ? (
          <ListSkeleton />
        ) : (
          <ul className="space-y-1 text-xs text-mist">
            {list.map((it) => (
              <li key={it.scenario_id} className="flex items-center gap-2">
                <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-tide" />
                {it.label}
              </li>
            ))}
          </ul>
        )}
      </div>

      {running ? (
        <div className="flex items-center gap-2">
          <button
            disabled
            className="min-h-11 flex-1 rounded-lg bg-tide/60 font-semibold text-foam/80"
          >
            <span className="inline-flex items-center gap-2">
              <span className="h-3 w-3 animate-spin rounded-full border-2 border-foam/70 border-t-transparent" />
              {s.running}
            </span>
          </button>
          <button
            onClick={cancel}
            className="min-h-11 rounded-lg border border-depth px-3 text-xs font-semibold text-mist transition-colors hover:text-foam focus-visible:ring-2 focus-visible:ring-surf"
          >
            {s.cancel}
          </button>
        </div>
      ) : (
        <button
          onClick={run}
          className="min-h-11 rounded-lg bg-tide font-semibold text-foam transition-colors hover:bg-surf focus-visible:ring-2 focus-visible:ring-surf"
        >
          {s.runSim}
        </button>
      )}

      {running && <p className="text-[11px] leading-snug text-mist">{s.simProgress}</p>}

      {error && (
        <div className="flex items-center gap-2 rounded-xl border border-coral/50 bg-coral/10 p-2 text-[11px] text-coral" role="status">
          <span className="min-w-0 flex-1">{error}</span>
          <button
            onClick={run}
            className="shrink-0 rounded-md border border-coral/60 px-2 py-1 font-bold transition-colors hover:bg-coral/20 focus-visible:ring-2 focus-visible:ring-coral"
          >
            {s.retry}
          </button>
        </div>
      )}

      {/* Results */}
      {results.length > 0 && (
        <>
          {/* Baseline access-lost note — only when the API returns the number (item 6) */}
          {baselineAccessLost != null && (
            <div className="rounded-xl border border-coral/40 bg-coral/10 p-2 text-[11px] leading-snug text-coral" role="note">
              Baseline: {baselineAccessLost}
              {baselineTrips != null ? ` of ${baselineTrips}` : ''} sample trips already
              lose access to closed grounds in this model.
            </div>
          )}

          <TradeoffChart
            scenarios={results}
            selectedId={selectedId}
            onSelect={setSelectedId}
            labels={{ xAxis: s.riskReduced, yAxis: s.fleetCost, frontier: s.efficient }}
          />

          <div className="flex flex-col gap-2">
            {results.map((r) => (
              <ScenarioCard
                key={r.scenario_id}
                r={r}
                selected={r.scenario_id === selectedId}
                onSelect={() => setSelectedId(r.scenario_id)}
                accessLostLabel={s.accessLostTrips}
                labels={{
                  efficient: s.efficient,
                  risk: s.deltaRisk,
                  effort: s.deltaEffort,
                  hours: s.deltaHours,
                  fuel: s.deltaFuel,
                }}
              />
            ))}
          </div>

          {/* Plain-language summary of the selected option */}
          {selected && selected.summary && (
            <div className="rounded-xl border border-kelp/40 bg-kelp/10 p-3">
              <h3 className="mb-1 text-[11px] font-bold uppercase tracking-wide text-kelp">
                {s.summary}
              </h3>
              <p className="text-xs leading-snug text-foam">{selected.summary}</p>
            </div>
          )}
        </>
      )}

      <p className="text-[10px] leading-snug text-mist/80">
        {s.effortNote}
        {conn !== 'online' && ' · Demo numbers (offline).'}
      </p>
    </aside>
  );
}

function ListSkeleton() {
  return (
    <div className="space-y-1.5">
      {[0, 1, 2].map((i) => (
        <div key={i} className="h-3 w-full animate-pulse rounded bg-current/30" />
      ))}
    </div>
  );
}

function ScenarioCard({
  r,
  selected,
  onSelect,
  labels,
  accessLostLabel,
}: {
  r: ScenarioResult;
  selected: boolean;
  onSelect: () => void;
  labels: { efficient: string; risk: string; effort: string; hours: string; fuel: string };
  accessLostLabel: string;
}) {
  return (
    <button
      onClick={onSelect}
      className={[
        'rounded-xl border p-3 text-left transition-colors focus-visible:ring-2 focus-visible:ring-surf',
        selected
          ? 'border-surf bg-surf/10'
          : r.on_frontier
            ? 'border-kelp/60 bg-kelp/5'
            : 'border-depth bg-abyss/50',
      ].join(' ')}
    >
      <div className="flex items-start justify-between gap-2">
        <span className="text-sm font-semibold text-foam">{r.label}</span>
        {r.on_frontier && (
          <span className="shrink-0 rounded-full bg-kelp/20 px-2 py-0.5 text-[10px] font-bold text-kelp">
            {labels.efficient}
          </span>
        )}
      </div>
      <div className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
        <Delta label={labels.risk} pct={r.delta_risk_pct} goodWhenNegative />
        <Delta label={labels.effort} pct={r.delta_effort_access_pct} />
        <Delta label={labels.hours} pct={r.delta_hours_pct} />
        <Delta label={labels.fuel} pct={r.delta_fuel_pct} />
      </div>
      {/* Access-lost trips for this scenario (only when the API returns it) */}
      {r.access_lost_trips != null && (
        <p className="mt-1.5 text-[11px] text-coral">
          {r.access_lost_trips} {accessLostLabel}
        </p>
      )}
    </button>
  );
}

function Delta({
  label,
  pct,
  goodWhenNegative = false,
}: {
  label: string;
  pct: number;
  goodWhenNegative?: boolean;
}) {
  const negative = pct < 0;
  const good = goodWhenNegative ? negative : !negative;
  return (
    <div className="flex justify-between gap-2">
      <span className="truncate text-mist">{label}</span>
      <span className={['shrink-0 font-mono', good ? 'text-kelp' : 'text-coral'].join(' ')}>
        {pct > 0 ? '+' : ''}
        {pct.toFixed(0)}%
      </span>
    </div>
  );
}
