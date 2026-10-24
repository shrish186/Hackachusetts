import { useEffect, useMemo, useRef, useState } from 'react';
import { api } from '@/api/client';
import type { AccessLost, NarrativeLine } from '@/api/client';
import type { AgentEvent, RoutePlan, TripRequest, VesselType } from '@/api/types';
import { useAppState } from '@/state/AppState';
import { usePorts, useZones } from '@/hooks/useLayerData';
import {
  REPLAY_WHALE_SEASON_ISO,
  datetimeLocalToIso,
  formatDepartureLabel,
  isoToDatetimeLocal,
} from '@/lib/time';
import { t, DISCLAIMER } from '@/lib/i18n';
import { recommendedIndex, classifyPlans, sortPlans } from '@/lib/recommend';
import {
  buildShareUrl,
  parsePlannerStateFromHash,
  type PlannerState,
} from '@/lib/shareLink';
import { LanguageSwitch } from '@/components/LanguageSwitch';
import { Combobox, type ComboOption } from '@/components/Combobox';
import { ClosedChip, closedRange } from '@/components/ClosedChip';
import { Toast } from '@/components/Toast';
import { AgentFeed } from './AgentFeed';
import { PlanCard } from './PlanCard';
import { PlanComparisonChart } from './PlanComparisonChart';

interface CaptainPanelProps {
  /** Called when the captain selects a plan (or clears it). Drives the map. */
  onSelectedRoute: (route: RoutePlan | null) => void;
}

const VESSELS: VesselType[] = ['small_boat', 'mid_trawler', 'scalloper'];

export function CaptainPanel({ onSelectedRoute }: CaptainPanelProps) {
  const {
    language,
    setLanguage,
    layerTimeIso,
    replay,
    setReplay,
    departure,
    setDeparture,
  } = useAppState();
  const s = t(language);

  const zones = useZones(layerTimeIso);
  const zoneName = useMemo(() => {
    const byId = new Map(zones.map((z) => [z.id, z.name]));
    return (id: string) => byId.get(id) ?? id;
  }, [zones]);

  // Ports + grounds (closed flags recomputed at the active layer time).
  const ports = usePorts(layerTimeIso);

  // Form state
  const [vessel, setVessel] = useState<VesselType>('mid_trawler');
  const [port, setPort] = useState('gloucester');
  const [ground, setGround] = useState(''); // '' = Any ground
  const [cruiseKn, setCruiseKn] = useState(9.5);
  const [maxHours, setMaxHours] = useState(14);
  const [riskPref, setRiskPref] = useState(0.6);

  // Result state
  const [loading, setLoading] = useState(false);
  const [coldStart, setColdStart] = useState(false);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [plans, setPlans] = useState<RoutePlan[]>([]);
  const [narrative, setNarrative] = useState<NarrativeLine[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [accessLost, setAccessLost] = useState<AccessLost | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const [hovered, setHovered] = useState<number | null>(null);
  const [lastTrip, setLastTrip] = useState<TripRequest | null>(null);
  const [resultRiskPref, setResultRiskPref] = useState(0.6);
  const [toast, setToast] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const coldTimerRef = useRef<number | null>(null);
  const restoredRef = useRef(false);

  const selectedPort = useMemo(() => ports.find((p) => p.id === port) ?? null, [ports, port]);
  const groundsForPort = selectedPort?.grounds ?? [];
  const selectedGround = groundsForPort.find((g) => g.id === ground) ?? null;

  const departureDate = useMemo(() => {
    const d = new Date(departure);
    return isNaN(d.getTime()) ? null : d;
  }, [departure]);

  function buildWindow(departISO: string, minLeadMs = 60_000): [string, string] {
    if (replay) return [REPLAY_WHALE_SEASON_ISO, REPLAY_WHALE_SEASON_ISO];
    const now = Date.now();
    let start = new Date(departISO).getTime();
    if (isNaN(start) || start < now + minLeadMs) start = now + minLeadMs;
    const end = start + 60 * 60 * 1000;
    return [new Date(start).toISOString(), new Date(end).toISOString()];
  }

  function requestFrom(overrides?: Partial<TripRequest>): TripRequest {
    return {
      port,
      vessel,
      cruise_kn: cruiseKn,
      max_hours: maxHours,
      depart_window: buildWindow(datetimeLocalToIso(departure)),
      target_ground: ground || null, // omit (null) for "Any ground"
      risk_pref: riskPref,
      language,
      ...overrides,
    };
  }

  async function plan(req: TripRequest, riskPrefUsed: number) {
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;

    setLoading(true);
    setColdStart(false);
    if (coldTimerRef.current) window.clearTimeout(coldTimerRef.current);
    coldTimerRef.current = window.setTimeout(() => setColdStart(true), 2000);

    setEvents([]);
    setPlans([]);
    setNarrative([]);
    setMessage(null);
    setAccessLost(null);
    setSelected(null);
    setHovered(null);
    setLastTrip(req);
    setResultRiskPref(riskPrefUsed);
    onSelectedRoute(null);

    try {
      const result = await api.planTripStream(req, {
        signal: ac.signal,
        onEvent: (ev) =>
          setEvents((prev) => {
            const i = prev.findIndex((p) => p.id === ev.id);
            if (i === -1) return [...prev, ev];
            const next = prev.slice();
            next[i] = ev;
            return next;
          }),
      });
      if (ac.signal.aborted) return;
      const ordered = sortPlans(result.plans);
      setPlans(ordered);
      setNarrative(result.narrative);
      setMessage(result.message);
      setAccessLost(result.access_lost);
      if (ordered.length > 0) {
        const rec = recommendedIndex(ordered, riskPrefUsed);
        setSelected(rec);
        onSelectedRoute(ordered[rec] ?? ordered[0]);
      }
    } finally {
      if (coldTimerRef.current) window.clearTimeout(coldTimerRef.current);
      if (!ac.signal.aborted) {
        setLoading(false);
        setColdStart(false);
      }
    }
  }

  // Restore planner state from the URL hash on first mount, then auto-run.
  useEffect(() => {
    if (restoredRef.current) return;
    restoredRef.current = true;
    const parsed = parsePlannerStateFromHash(window.location.hash);
    if (Object.keys(parsed).length === 0) return;

    if (parsed.vessel) setVessel(parsed.vessel);
    if (parsed.port) setPort(parsed.port);
    if (parsed.ground !== undefined) setGround(parsed.ground);
    if (parsed.cruiseKn !== undefined) setCruiseKn(parsed.cruiseKn);
    if (parsed.maxHours !== undefined) setMaxHours(parsed.maxHours);
    if (parsed.riskPref !== undefined) setRiskPref(parsed.riskPref);
    if (parsed.language) setLanguage(parsed.language);
    if (parsed.replay !== undefined) setReplay(parsed.replay);
    if (parsed.departure && parsed.replay !== true) setDeparture(parsed.departure);

    const rp = parsed.riskPref ?? 0.6;
    const req: TripRequest = {
      port: parsed.port ?? 'gloucester',
      vessel: parsed.vessel ?? 'mid_trawler',
      cruise_kn: parsed.cruiseKn ?? 9.5,
      max_hours: parsed.maxHours ?? 14,
      depart_window: parsed.replay
        ? [REPLAY_WHALE_SEASON_ISO, REPLAY_WHALE_SEASON_ISO]
        : buildWindow(datetimeLocalToIso(parsed.departure ?? departure)),
      target_ground: parsed.ground || null,
      risk_pref: rp,
      language: parsed.language ?? language,
    };
    // Defer so state setters have applied before the run reads them.
    window.setTimeout(() => void plan(req, rp), 0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => () => abortRef.current?.abort(), []);

  function runDemo() {
    setPort('gloucester');
    setVessel('small_boat');
    setGround('stellwagen_bank');
    setCruiseKn(9);
    setMaxHours(12);
    setRiskPref(0.8);
    setReplay(true);
    setDeparture(isoToDatetimeLocal(REPLAY_WHALE_SEASON_ISO));
    void plan(
      {
        port: 'gloucester',
        vessel: 'small_boat',
        cruise_kn: 9,
        max_hours: 12,
        depart_window: [REPLAY_WHALE_SEASON_ISO, REPLAY_WHALE_SEASON_ISO],
        target_ground: 'stellwagen_bank',
        risk_pref: 0.8,
        language,
      },
      0.8,
    );
  }

  function planToNearestOpen() {
    const n = accessLost?.nearest_open;
    if (!n) return;
    void plan(requestFrom({ target_ground: `${n.lon.toFixed(3)},${n.lat.toFixed(3)}` }), riskPref);
  }

  async function copyShareLink() {
    const st: PlannerState = {
      port,
      vessel,
      cruiseKn,
      maxHours,
      departure,
      ground,
      riskPref,
      replay,
      language,
    };
    const url = buildShareUrl(st);
    // Keep the address bar in sync so a plain reload also restores state.
    try {
      window.history.replaceState(null, '', url);
    } catch {
      /* ignore */
    }
    try {
      await navigator.clipboard.writeText(url);
    } catch {
      /* clipboard may be blocked; the URL is still in the address bar */
    }
    setToast(s.linkCopied);
  }

  function selectPlan(i: number) {
    setSelected(i);
    onSelectedRoute(plans[i]);
  }

  const recIdx = plans.length ? recommendedIndex(plans, resultRiskPref) : -1;
  const planClasses = useMemo(() => classifyPlans(plans), [plans]);
  const activeIdx = hovered ?? selected;

  // Port combobox options.
  const portOptions: ComboOption[] = ports.map((p) => ({
    id: p.id,
    label: p.name,
    keywords: p.id,
    badge: 'MA',
    subtitle: `${p.lat.toFixed(3)}, ${p.lon.toFixed(3)}`,
  }));

  // Ground combobox options ("Any ground" + the selected port's grounds).
  const groundOptions: ComboOption[] = [
    { id: '', label: s.anyGround },
    ...groundsForPort.map((g) => ({
      id: g.id,
      label: g.name,
      keywords: g.id,
      subtitle: `${g.lat.toFixed(3)}, ${g.lon.toFixed(3)}`,
      chip: g.closed ? <ClosedChip ground={g} language={language} /> : undefined,
    })),
  ];

  const portValid = !!selectedPort;

  return (
    <aside className="pointer-events-auto flex w-80 max-w-[88vw] flex-col gap-3 rounded-2xl border border-depth bg-deep/85 p-4 backdrop-blur">
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-sm font-bold text-foam">{s.planTripTitle}</h2>
        <div className="w-28">
          <LanguageSwitch value={language} onChange={setLanguage} />
        </div>
      </div>

      {/* Port picker (item 1) */}
      <label className="text-xs text-mist">
        {s.port}
        <Combobox
          label={s.port}
          options={portOptions}
          value={port}
          onChange={setPort}
          placeholder={s.portPlaceholder}
          invalidMessage={s.pickPort}
        />
      </label>

      {/* Ground picker (item 2) */}
      <label className="text-xs text-mist">
        {s.ground}
        <Combobox
          label={s.ground}
          options={groundOptions}
          value={ground}
          onChange={setGround}
          placeholder={s.groundPlaceholder}
          invalidMessage={s.pickPort}
        />
        {selectedGround?.closed && (
          <span className="mt-1 flex items-center gap-1.5 text-[11px] text-alert">
            <ClosedChip ground={selectedGround} language={language} />
            <span className="text-mist">{selectedGround.closed_reason}</span>
          </span>
        )}
      </label>

      {/* Vessel */}
      <div className="text-xs text-mist">
        {s.vessel}
        <div className="mt-1 flex gap-1" role="group" aria-label={s.vessel}>
          {VESSELS.map((v) => (
            <button
              key={v}
              onClick={() => setVessel(v)}
              aria-pressed={vessel === v}
              className={[
                'flex-1 rounded-lg border px-2 py-2 text-[11px] font-semibold transition-colors focus-visible:ring-2 focus-visible:ring-surf',
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
            aria-label={s.cruiseSpeed}
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
            aria-label={s.maxHours}
            className="mt-1 w-full rounded-lg border border-depth bg-abyss/60 px-3 py-2 text-sm text-foam outline-none focus:border-surf focus-visible:ring-2 focus-visible:ring-surf"
          />
        </label>
      </div>

      {/* Departure (shared with the time slider) */}
      <label className="text-xs text-mist">
        {s.departure}
        <input
          type="datetime-local"
          value={departure}
          onChange={(e) => setDeparture(e.target.value)}
          aria-label={s.departure}
          className="mt-1 w-full rounded-lg border border-depth bg-abyss/60 px-3 py-2 text-sm text-foam outline-none focus:border-surf focus-visible:ring-2 focus-visible:ring-surf [color-scheme:dark]"
        />
        {departureDate && (
          <span className="mt-1 block text-[11px] text-surf">
            {formatDepartureLabel(departureDate)}
          </span>
        )}
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
          aria-label={`${s.fastest} / ${s.safest}`}
          className="mt-1 h-8 w-full cursor-pointer accent-surf"
        />
      </label>

      <div className="flex gap-2">
        <button
          onClick={() => void plan(requestFrom(), riskPref)}
          disabled={loading || !portValid}
          className="min-h-11 flex-1 rounded-lg bg-tide font-semibold text-foam transition-colors hover:bg-surf disabled:opacity-60 focus-visible:ring-2 focus-visible:ring-surf"
        >
          {loading ? s.planning : s.planRoutes}
        </button>
        <button
          onClick={runDemo}
          disabled={loading}
          title={s.tryDemoHint}
          className="min-h-11 rounded-lg border border-surf/60 px-3 text-xs font-semibold text-surf transition-colors hover:bg-surf/15 disabled:opacity-60 focus-visible:ring-2 focus-visible:ring-surf"
        >
          {s.tryDemo}
        </button>
      </div>

      {/* Copy shareable link (item 4) */}
      <button
        onClick={copyShareLink}
        className="min-h-9 rounded-lg border border-depth px-3 text-xs font-semibold text-mist transition-colors hover:text-foam focus-visible:ring-2 focus-visible:ring-surf"
      >
        🔗 {s.copyLink}
      </button>

      {/* Cold-start hint while the free server wakes (item 5) */}
      {loading && coldStart && (
        <p className="rounded-xl border border-surf/40 bg-surf/10 p-2 text-[11px] leading-snug text-surf" role="status">
          {s.planningCold}
        </p>
      )}

      {/* Live agent feed */}
      <AgentFeed events={events} language={language} active={loading} />

      {/* Empty state before the first plan */}
      {!loading && plans.length === 0 && !message && !accessLost && events.length === 0 && (
        <p className="rounded-xl border border-dashed border-depth bg-abyss/30 p-3 text-center text-[11px] leading-snug text-mist">
          {s.tryDemoHint}
        </p>
      )}

      {/* Access-lost card (item 4 prior round) */}
      {accessLost && (
        <div className="rounded-xl border border-coral/60 bg-coral/10 p-3 text-xs" role="status">
          <p className="font-semibold text-coral">
            🔒 {s.accessLostTitle}{' '}
            <span className="text-foam">
              {accessLost.zone_name ?? accessLost.reason ?? accessLost.code}
            </span>
          </p>
          {accessLost.nearest_open && (
            <>
              <p className="mt-1 text-mist">
                {s.nearestOpen}{' '}
                <span className="font-mono text-foam">
                  {accessLost.nearest_open.lat.toFixed(3)}, {accessLost.nearest_open.lon.toFixed(3)}
                </span>{' '}
                ({accessLost.nearest_open.distance_nm.toFixed(1)} nm)
              </p>
              <button
                onClick={planToNearestOpen}
                disabled={loading}
                className="mt-2 min-h-9 w-full rounded-lg bg-tide px-3 text-xs font-semibold text-foam transition-colors hover:bg-surf disabled:opacity-60 focus-visible:ring-2 focus-visible:ring-surf"
              >
                {s.planToNearest}
              </button>
            </>
          )}
        </div>
      )}

      {/* No legal route message */}
      {message && !accessLost && (
        <div className="rounded-xl border border-coral/50 bg-coral/10 p-3 text-xs text-coral" role="status">
          {message}
        </div>
      )}

      {/* Single-route note */}
      {plans.length === 1 && (
        <p className="rounded-xl border border-depth bg-abyss/30 p-2 text-center text-[11px] leading-snug text-mist">
          {s.singleRouteNote}
        </p>
      )}

      {/* Plan comparison chart (item 3) */}
      {plans.length > 1 && (
        <div className="rounded-xl border border-depth bg-abyss/40 p-2">
          <PlanComparisonChart
            plans={plans}
            planClasses={planClasses}
            recommendedIdx={recIdx}
            activeIdx={activeIdx}
            onHover={setHovered}
            onSelect={selectPlan}
            language={language}
          />
        </div>
      )}

      {/* Ranked plan cards */}
      {plans.length > 0 && (
        <div className="flex flex-col gap-2">
          {plans.map((p, i) => (
            <PlanCard
              key={i}
              plan={p}
              planClass={planClasses[i]}
              recommended={i === recIdx}
              plans={plans}
              language={language}
              selected={selected === i}
              highlighted={hovered === i}
              onSelect={() => selectPlan(i)}
              onHover={() => setHovered(i)}
              onLeave={() => setHovered(null)}
              zoneName={zoneName}
              trip={lastTrip ?? undefined}
              narrative={narrative}
            />
          ))}
        </div>
      )}

      {/* Always-visible advisory disclaimer */}
      <p className="text-center text-[10px] leading-snug text-mist/80">
        {DISCLAIMER[language]}
      </p>

      <Toast message={toast} onDone={() => setToast(null)} />
    </aside>
  );
}

// Re-export for tests / external use if needed.
export { closedRange };
