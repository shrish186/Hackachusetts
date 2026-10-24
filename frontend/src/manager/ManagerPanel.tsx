import { useEffect, useState } from 'react';
import { api } from '@/api/client';
import type { ScenarioResult } from '@/api/types';

/**
 * Manager mode panel. This scaffold loads the (mocked) scenario comparison and
 * shows the trade-off list with the efficient-frontier highlight. The draw tool
 * and trade-off chart are Phase 3 work (tasks.md 3.5).
 */
export function ManagerPanel() {
  const [scenarios, setScenarios] = useState<ScenarioResult[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    api.runScenario().then((s) => {
      if (alive) {
        setScenarios(s);
        setLoading(false);
      }
    });
    return () => {
      alive = false;
    };
  }, []);

  return (
    <aside className="pointer-events-auto flex w-80 max-w-[88vw] flex-col gap-3 rounded-2xl border border-depth bg-deep/85 p-4 backdrop-blur">
      <h2 className="text-sm font-bold text-foam">What-if simulator</h2>
      <p className="text-xs text-mist">
        Compare candidate protection zones. Fewer whale strikes vs. livelihood
        cost. Highlighted options are on the efficient frontier.
      </p>

      {loading && <div className="text-xs text-mist">Running fleet re-route…</div>}

      <div className="flex flex-col gap-2 overflow-y-auto">
        {scenarios.map((s) => (
          <ScenarioCard key={s.scenario_id} s={s} />
        ))}
      </div>

      <p className="pointer-events-none text-[10px] leading-snug text-mist/80">
        Effort access is an estimate, not catch or revenue. Synthetic fleet for
        the demo.
      </p>
    </aside>
  );
}

function ScenarioCard({ s }: { s: ScenarioResult }) {
  return (
    <div
      className={[
        'rounded-xl border p-3',
        s.on_frontier ? 'border-kelp/70 bg-kelp/10' : 'border-depth bg-abyss/50',
      ].join(' ')}
    >
      <div className="flex items-start justify-between gap-2">
        <span className="text-sm font-semibold text-foam">{s.label}</span>
        {s.on_frontier && (
          <span className="shrink-0 rounded-full bg-kelp/20 px-2 py-0.5 text-[10px] font-bold text-kelp">
            efficient
          </span>
        )}
      </div>
      <div className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
        <Delta label="Risk" pct={s.delta_risk_pct} goodWhenNegative />
        <Delta label="Effort access" pct={s.delta_effort_access_pct} />
        <Delta label="Steaming hrs" pct={s.delta_hours_pct} />
        <Delta label="Fuel" pct={s.delta_fuel_pct} />
      </div>
      <p className="mt-2 text-[11px] leading-snug text-mist">{s.summary}</p>
    </div>
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
    <div className="flex justify-between">
      <span className="text-mist">{label}</span>
      <span className={['font-mono', good ? 'text-kelp' : 'text-coral'].join(' ')}>
        {pct > 0 ? '+' : ''}
        {pct.toFixed(0)}%
      </span>
    </div>
  );
}
