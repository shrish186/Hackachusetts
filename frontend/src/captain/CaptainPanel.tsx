import { useMemo, useRef, useState } from 'react';
import { api } from '@/api/client';
import type { AgentEvent, RoutePlan, VesselType } from '@/api/types';
import { useAppState } from '@/state/AppState';
import { useZones } from '@/hooks/useLayerData';
import { sliceToIso } from '@/lib/time';
import { t, DISCLAIMER } from '@/lib/i18n';
import { LanguageSwitch } from '@/components/LanguageSwitch';
import { AgentFeed } from './AgentFeed';
import { PlanCard } from './PlanCard';

interface CaptainPanelProps {
  /** Called when the captain selects a plan (or clears it). Drives the map. */
  onSelectedRoute: (route: RoutePlan | null) => void;
}

const VESSELS: VesselType[] = ['small_boat', 'mid_trawler', 'scalloper'];

/**
 * Captain mode request panel (tasks.md 2.8 + 2.9).
 *
 * Trip request form → streamed agent feed → 2–3 ranked plan cards. Selecting a
 * card draws its route on the map. Each card has a "Why" drawer and the
 * advisory disclaimer. A language switch re-renders all plan text in
 * English / Portuguese / Spanish (numbers + zone names stay identical).
 */
export function CaptainPanel({ onSelectedRoute }: CaptainPanelProps) {
  const { language, setLanguage, sliceIndex } = useAppState();
  const s = t(language);

  // Resolve zone ids → display names (loaded once; names are language-neutral).
  const zones = useZones(sliceToIso(sliceIndex));
  const zoneName = useMemo(() => {
    const byId = new Map(zones.map((z) => [z.id, z.name]));
    return (id: string) => byId.get(id) ?? id;
  }, [zones]);

  // Form state
  const [vessel, setVessel] = useState<VesselType>('mid_trawler');
  const [port, setPort] = useState('provincetown');
  const [cruiseKn, setCruiseKn] = useState(9.5);
  const [maxHours, setMaxHours] = useState(14);
  const [departure, setDeparture] = useState('2026-03-15T09:00');
  const [riskPref, setRiskPref] = useState(0.6);

  // Result state
  const [loading, setLoading] = useState(false);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [plans, setPlans] = useState<RoutePlan[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  async function plan() {
    // Reset prior run.
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;

    setLoading(true);
    setEvents([]);
    setPlans([]);
    setSelected(null);
    onSelectedRoute(null);

    const departIso = new Date(departure).toISOString();
    try {
      const routes = await api.planTripStream(
        {
          port,
          vessel,
          cruise_kn: cruiseKn,
          max_hours: maxHours,
          depart_window: [departIso, departIso],
          target_ground: 'stellwagen_bank',
          risk_pref: riskPref,
          language,
        },
        {
          signal: ac.signal,
          onEvent: (ev) =>
            setEvents((prev) => {
              // Replace the running placeholder with its done state (same id).
              const i = prev.findIndex((p) => p.id === ev.id);
              if (i === -1) return [...prev, ev];
              const next = prev.slice();
              next[i] = ev;
              return next;
            }),
        },
      );
      if (ac.signal.aborted) return;
      setPlans(routes);
      // Auto-select the top-ranked plan and draw it.
      setSelected(0);
      onSelectedRoute(routes[0] ?? null);
    } finally {
      if (!ac.signal.aborted) setLoading(false);
    }
  }

  function selectPlan(i: number) {
    setSelected(i);
    onSelectedRoute(plans[i]);
  }

  return (
    <aside className="pointer-events-auto flex max-h-[calc(100vh-10rem)] w-80 max-w-[88vw] flex-col gap-3 overflow-y-auto rounded-2xl border border-depth bg-deep/85 p-4 backdrop-blur">
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-sm font-bold text-foam">{s.planTripTitle}</h2>
        <div className="w-28">
          <LanguageSwitch value={language} onChange={setLanguage} />
        </div>
      </div>

      {/* Port */}
      <label className="text-xs text-mist">
        {s.port}
        <input
          value={port}
          onChange={(e) => setPort(e.target.value)}
          className="mt-1 w-full rounded-lg border border-depth bg-abyss/60 px-3 py-2 text-sm text-foam outline-none focus:border-surf"
        />
      </label>

      {/* Vessel */}
      <div className="text-xs text-mist">
        {s.vessel}
        <div className="mt-1 flex gap-1">
          {VESSELS.map((v) => (
            <button
              key={v}
              onClick={() => setVessel(v)}
              className={[
                'flex-1 rounded-lg border px-2 py-2 text-[11px] font-semibold transition-colors',
                vessel === v
                  ? 'border-tide bg-tide/30 text-foam'
                  : 'border-depth text-mist hover:text-foam',
              ].join(' ')}
            >
              {s[v]}
            </button>
          ))}
        </div>
      </div>

      {/* Speed + max hours */}
      <div className="grid grid-cols-2 gap-2">
        <label className="text-xs text-mist">
          <div className="flex justify-between">
            <span>{s.cruiseSpeed}</span>
            <span className="font-mono text-foam">
              {cruiseKn} {s.knots}
            </span>
          </div>
          <input
            type="range"
            min={4}
            max={18}
            step={0.5}
            value={cruiseKn}
            onChange={(e) => setCruiseKn(Number(e.target.value))}
            className="mt-1 h-8 w-full cursor-pointer accent-surf"
          />
        </label>
        <label className="text-xs text-mist">
          {s.maxHours}
          <input
            type="number"
            min={1}
            max={48}
            step={1}
            value={maxHours}
            onChange={(e) => setMaxHours(Number(e.target.value))}
            className="mt-1 w-full rounded-lg border border-depth bg-abyss/60 px-3 py-2 text-sm text-foam outline-none focus:border-surf"
          />
        </label>
      </div>

      {/* Departure */}
      <label className="text-xs text-mist">
        {s.departure}
        <input
          type="datetime-local"
          value={departure}
          onChange={(e) => setDeparture(e.target.value)}
          className="mt-1 w-full rounded-lg border border-depth bg-abyss/60 px-3 py-2 text-sm text-foam outline-none focus:border-surf [color-scheme:dark]"
        />
      </label>

      {/* Risk vs speed slider */}
      <label className="text-xs text-mist">
        <div className="flex justify-between">
          <span>{s.fastest}</span>
          <span className="font-mono text-foam">{riskPref.toFixed(1)}</span>
          <span>{s.safest}</span>
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
        {loading ? s.planning : s.planRoutes}
      </button>

      {/* Live agent feed */}
      <AgentFeed events={events} language={language} active={loading} />

      {/* Ranked plan cards */}
      {plans.length > 0 && (
        <div className="flex flex-col gap-2">
          {plans.map((p, i) => (
            <PlanCard
              key={i}
              plan={p}
              rank={i + 1}
              language={language}
              selected={selected === i}
              onSelect={() => selectPlan(i)}
              zoneName={zoneName}
            />
          ))}
        </div>
      )}

      {/* Always-visible advisory disclaimer */}
      <p className="pointer-events-none text-center text-[10px] leading-snug text-mist/80">
        {DISCLAIMER[language]}
      </p>
    </aside>
  );
}
