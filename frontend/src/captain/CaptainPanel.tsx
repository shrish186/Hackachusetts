import { useState } from 'react';
import { api } from '@/api/client';
import type { RoutePlan, VesselType } from '@/api/types';
import { Disclaimer } from '@/components/Disclaimer';

interface CaptainPanelProps {
  onRoutes: (routes: RoutePlan[]) => void;
}

const VESSELS: { id: VesselType; label: string }[] = [
  { id: 'small_boat', label: 'Small boat' },
  { id: 'mid_trawler', label: 'Mid trawler' },
  { id: 'scalloper', label: 'Scalloper' },
];

/**
 * Captain mode request panel. This scaffold wires the request form to the
 * (mocked) trip planner so routes render on the map; the streaming tool-call
 * feed and ranked plan cards are Phase 2 work (tasks.md 2.8–2.9).
 */
export function CaptainPanel({ onRoutes }: CaptainPanelProps) {
  const [vessel, setVessel] = useState<VesselType>('mid_trawler');
  const [port, setPort] = useState('provincetown');
  const [riskPref, setRiskPref] = useState(0.6);
  const [loading, setLoading] = useState(false);
  const [plans, setPlans] = useState<RoutePlan[]>([]);

  async function plan() {
    setLoading(true);
    try {
      const routes = await api.planTrip({
        port,
        vessel,
        cruise_kn: 9.5,
        max_hours: 14,
        depart_window: ['2026-03-15T09:00:00Z', '2026-03-15T13:00:00Z'],
        target_ground: 'stellwagen_bank',
        risk_pref: riskPref,
        language: 'en',
      });
      setPlans(routes);
      onRoutes(routes);
    } finally {
      setLoading(false);
    }
  }

  return (
    <aside className="pointer-events-auto flex w-80 max-w-[88vw] flex-col gap-3 rounded-2xl border border-depth bg-deep/85 p-4 backdrop-blur">
      <h2 className="text-sm font-bold text-foam">Plan a trip</h2>

      <label className="text-xs text-mist">
        Port
        <input
          value={port}
          onChange={(e) => setPort(e.target.value)}
          className="mt-1 w-full rounded-lg border border-depth bg-abyss/60 px-3 py-2 text-sm text-foam outline-none focus:border-surf"
        />
      </label>

      <div className="text-xs text-mist">
        Vessel
        <div className="mt-1 flex gap-1">
          {VESSELS.map((v) => (
            <button
              key={v.id}
              onClick={() => setVessel(v.id)}
              className={[
                'flex-1 rounded-lg border px-2 py-2 text-xs font-semibold transition-colors',
                vessel === v.id
                  ? 'border-tide bg-tide/30 text-foam'
                  : 'border-depth text-mist hover:text-foam',
              ].join(' ')}
            >
              {v.label}
            </button>
          ))}
        </div>
      </div>

      <label className="text-xs text-mist">
        <div className="flex justify-between">
          <span>Fastest ↔ Safest</span>
          <span className="font-mono text-foam">{riskPref.toFixed(1)}</span>
        </div>
        <input
          type="range"
          min={0}
          max={1}
          step={0.1}
          value={riskPref}
          onChange={(e) => setRiskPref(Number(e.target.value))}
          className="mt-1 h-8 w-full cursor-pointer accent-surf"
        />
      </label>

      <button
        onClick={plan}
        disabled={loading}
        className="min-h-11 rounded-lg bg-tide font-semibold text-foam transition-colors hover:bg-surf disabled:opacity-60"
      >
        {loading ? 'Planning…' : 'Plan routes'}
      </button>

      <div className="flex flex-col gap-2 overflow-y-auto">
        {plans.map((p, i) => (
          <PlanCard key={i} plan={p} rank={i + 1} />
        ))}
      </div>

      <Disclaimer />
    </aside>
  );
}

function PlanCard({ plan, rank }: { plan: RoutePlan; rank: number }) {
  return (
    <div className="rounded-xl border border-depth bg-abyss/50 p-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-bold text-foam">Option {rank}</span>
        <span className="rounded-full bg-kelp/20 px-2 py-0.5 text-xs font-semibold text-kelp">
          risk {plan.risk_exposure.toFixed(2)}
        </span>
      </div>
      <dl className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-xs text-mist">
        <Stat label="ETA" value={`${plan.eta_hours.toFixed(1)} h`} />
        <Stat label="Fuel (est.)" value={`${plan.fuel_est_l.toFixed(0)} L`} />
        <Stat label="Max wave" value={`${plan.max_wave_m.toFixed(1)} m`} />
        <Stat label="Effort (est.)" value={plan.effort_proxy.toFixed(2)} />
      </dl>
      {plan.zones_crossed.length > 0 && (
        <p className="mt-2 text-[11px] text-mist">
          Avoids closures; crosses {plan.zones_crossed.length} managed zone
          {plan.zones_crossed.length > 1 ? 's' : ''}.
        </p>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between">
      <dt>{label}</dt>
      <dd className="font-mono text-foam">{value}</dd>
    </div>
  );
}
