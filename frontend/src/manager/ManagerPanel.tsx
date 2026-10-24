import { useEffect, useState } from 'react';
import { api } from '@/api/client';
import type { ScenarioListItem, ScenarioResult } from '@/api/types';
import { useAppState } from '@/state/AppState';
import { useConn } from '@/hooks/useConn';
import { t } from '@/lib/i18n';
import { TradeoffChart } from './TradeoffChart';

/**
 * Manager mode panel (tasks.md task 4).
 *
 * - Polygon draw tool (vertices placed on the map; finish/clear here)
 * - Scenario list from GET /api/sim/scenarios
 * - Run button -> POST /api/sim/run (with the drawn polygon if any)
 * - SVG trade-off chart (risk reduced vs fleet cost) with the efficient
 *   frontier highlighted
 * - Plain-language summary in the selected language
 * Falls back to realistic mock numbers (labeled demo) when offline.
 */
export function ManagerPanel() {
  const { language, drawing, setDrawing, drawnPolygon, setDrawnPolygon } = useAppState();
  const conn = useConn();
  const s = t(language);

  const [list, setList] = useState<ScenarioListItem[]>([]);
  const [results, setResults] = useState<ScenarioResult[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [loadingList, setLoadingList] = useState(true);

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

  async function run() {
    setRunning(true);
    try {
      const res = await api.runScenario({
        polygon: drawnPolygon.length >= 3 ? drawnPolygon : undefined,
      });
      setResults(res);
      // Pick the first efficient option (or the first result) as selected.
      const firstFrontier = res.find((r) => r.on_frontier) ?? res[0];
      setSelectedId(firstFrontier?.scenario_id ?? null);
    } finally {
      setRunning(false);
    }
  }

  const selected = results.find((r) => r.scenario_id === selectedId) ?? null;

  return (
    <aside className="pointer-events-auto flex max-h-[calc(100vh-10rem)] w-80 max-w-[88vw] flex-col gap-3 overflow-y-auto rounded-2xl border border-depth bg-deep/85 p-4 backdrop-blur">
      <h2 className="text-sm font-bold text-foam">{s.simTitle}</h2>
      <p className="text-xs leading-snug text-mist">{s.simIntro}</p>

      {/* Draw tool */}
      <div className="rounded-xl border border-depth bg-abyss/40 p-3">
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setDrawing((d) => !d)}
            aria-pressed={drawing}
            className={[
              'min-h-9 flex-1 rounded-lg px-3 text-xs font-semibold transition-colors',
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
            className="min-h-9 rounded-lg border border-depth px-3 text-xs font-semibold text-mist transition-colors hover:text-foam disabled:opacity-50"
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
                <span className="h-1.5 w-1.5 rounded-full bg-tide" />
                {it.label}
              </li>
            ))}
          </ul>
        )}
      </div>

      <button
        onClick={run}
        disabled={running}
        className="min-h-11 rounded-lg bg-tide font-semibold text-foam transition-colors hover:bg-surf disabled:opacity-60"
      >
        {running ? s.running : s.runSim}
      </button>

      {/* Results */}
      {results.length > 0 && (
        <>
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
          {selected && (
            <div className="rounded-xl border border-kelp/40 bg-kelp/10 p-3">
              <h3 className="mb-1 text-[11px] font-bold uppercase tracking-wide text-kelp">
                {s.summary}
              </h3>
              <p className="text-xs leading-snug text-foam">{selected.summary}</p>
            </div>
          )}
        </>
      )}

      <p className="pointer-events-none text-[10px] leading-snug text-mist/80">
        {s.effortNote}
        {conn === 'offline' && ' · Demo numbers (offline).'}
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
}: {
  r: ScenarioResult;
  selected: boolean;
  onSelect: () => void;
  labels: { efficient: string; risk: string; effort: string; hours: string; fuel: string };
}) {
  return (
    <button
      onClick={onSelect}
      className={[
        'rounded-xl border p-3 text-left transition-colors',
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
