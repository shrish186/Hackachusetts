import { useState } from 'react';
import type { NarrativeLine } from '@/api/client';
import type { Language, RoutePlan, TripRequest } from '@/api/types';
import { t, riskLevelWord, DISCLAIMER, planClassLabel, tradeoffLine } from '@/lib/i18n';
import type { PlanClass } from '@/lib/recommend';
import { formatLocalShort } from '@/lib/time';
import { openBrief } from '@/lib/brief';

interface PlanCardProps {
  plan: RoutePlan;
  /** Fastest / Balanced / Safest label (task 10). */
  planClass: PlanClass;
  /** True when this is the scored recommendation (task 5). */
  recommended: boolean;
  /** All plans in the set, for trade-off vs the fastest option. */
  plans: RoutePlan[];
  language: Language;
  selected: boolean;
  /** Highlighted from the comparison chart hover (item 3). */
  highlighted?: boolean;
  onSelect: () => void;
  onHover?: () => void;
  onLeave?: () => void;
  /** Resolve a zone id to its display name (names stay identical across langs). */
  zoneName: (id: string) => string;
  /** The trip request this plan answers (for the printable brief). */
  trip?: TripRequest;
  /** Agent narrative lines (shown in the "why" drawer when present). */
  narrative?: NarrativeLine[];
}

/**
 * A ranked trip plan card (requirements.md Req 4.1/4.2; tasks 8 + 10).
 * Shows a plain label (Fastest/Balanced/Safest), a one-line trade-off, and an
 * "Advisory only" line. Selecting it draws the route on the map. The "Why"
 * drawer shows zones crossed, a risk summary, the weather window, and every
 * claim's citation (null source_url → "bundled demo data", never an empty link).
 */
export function PlanCard({
  plan,
  planClass,
  recommended,
  plans,
  language,
  selected,
  highlighted,
  onSelect,
  onHover,
  onLeave,
  zoneName,
  trip,
  narrative,
}: PlanCardProps) {
  const [open, setOpen] = useState(false);
  const s = t(language);

  // Trade-off vs the fastest plan (lowest ETA).
  const fastest = plans.reduce((a, b) => (b.eta_hours < a.eta_hours ? b : a), plans[0]);
  const deltaMin = (plan.eta_hours - fastest.eta_hours) * 60;
  const riskChangePct =
    fastest.risk_exposure > 0
      ? ((plan.risk_exposure - fastest.risk_exposure) / fastest.risk_exposure) * 100
      : 0;
  const showTradeoff = plans.length > 1 && plan !== fastest;

  return (
    <div
      onMouseEnter={onHover}
      onMouseLeave={onLeave}
      className={[
        'rounded-xl border p-3 transition-colors',
        selected
          ? 'border-surf bg-surf/10'
          : highlighted
            ? 'border-surf/70 bg-surf/5'
            : 'border-depth bg-abyss/50',
      ].join(' ')}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="min-w-0">
          <span className="text-sm font-bold text-foam">
            {planClassLabel(language, planClass)}
          </span>
          {plan.name && (
            <span className="ml-2 text-[11px] text-mist">{plan.name}</span>
          )}
          {recommended && (
            <span className="ml-2 rounded-full bg-kelp/20 px-2 py-0.5 text-[10px] font-bold text-kelp">
              {s.recommended}
            </span>
          )}
        </div>
        <span className="shrink-0 rounded-full bg-tide/25 px-2 py-0.5 text-xs font-semibold text-surf">
          {s.risk} {plan.risk_exposure.toFixed(2)}
        </span>
      </div>

      {/* Trade-off one-liner (task 10) */}
      {showTradeoff && (
        <p className="mt-1 text-[11px] text-mist">
          {tradeoffLine(language, deltaMin, riskChangePct)} {s.vsFastest}
        </p>
      )}

      <dl className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-xs text-mist">
        <Stat label={s.eta} value={`${plan.eta_hours.toFixed(1)} ${s.hours}`} />
        <Stat label={s.fuelEst} value={`${plan.fuel_est_l.toFixed(0)} ${s.liters}`} />
        <Stat label={s.maxWave} value={`${plan.max_wave_m.toFixed(1)} ${s.meters}`} />
        <Stat label={s.effortEst} value={plan.effort_proxy.toFixed(2)} />
      </dl>

      {/* Advisory-only line on every option (task 10 / Req 9.1) */}
      <p className="mt-1 text-[10px] font-semibold uppercase tracking-wide text-mist/70">
        {s.advisoryShort}
      </p>

      <div className="mt-3 flex items-center gap-2">
        <button
          onClick={onSelect}
          className={[
            'min-h-9 flex-1 rounded-lg px-3 text-xs font-semibold transition-colors focus-visible:ring-2 focus-visible:ring-surf',
            selected ? 'bg-surf text-abyss' : 'bg-tide text-foam hover:bg-surf',
          ].join(' ')}
        >
          {selected ? s.shownOnMap : s.showOnMap}
        </button>
        <button
          onClick={() => setOpen((o) => !o)}
          aria-expanded={open}
          className="min-h-9 rounded-lg border border-depth px-3 text-xs font-semibold text-mist transition-colors hover:text-foam focus-visible:ring-2 focus-visible:ring-surf"
        >
          {open ? s.hide : s.why}
        </button>
      </div>

      {open && (
        <div className="mt-3 space-y-3 border-t border-depth pt-3 text-xs">
          {/* Explainer vs Fastest (item 6) — computed only from API fields */}
          {showTradeoff && (
            <p className="text-mist">
              {s.comparedWith}{' '}
              {(() => {
                // Prefer backend vs_fastest fields; fall back to computed deltas.
                const extraMin =
                  plan.vs_fastest?.extra_hours != null
                    ? Math.round(plan.vs_fastest.extra_hours * 60)
                    : Math.round(deltaMin);
                const riskChange =
                  plan.vs_fastest?.risk_change != null
                    ? plan.vs_fastest.risk_change * 100
                    : riskChangePct;
                const lessPct = Math.max(0, Math.round(-riskChange));
                // Closures avoided: explicit field if present, else zones the
                // fastest crosses that this plan does not.
                const avoided =
                  plan.zones_avoided?.length ??
                  fastest.zones_crossed.filter((z) => !plan.zones_crossed.includes(z)).length;
                const avoidText =
                  avoided > 0
                    ? s.avoidsClosures.replace('{n}', String(avoided))
                    : s.avoidsNoClosures;
                return (
                  <span className="text-foam">
                    +{extraMin} min, {lessPct}% {s.lessRisk}, {avoidText}
                  </span>
                );
              })()}
            </p>
          )}

          {/* Zones crossed */}
          <section>
            <h4 className="mb-1 font-bold text-foam">{s.zonesCrossed}</h4>
            {plan.zones_crossed.length === 0 ? (
              <p className="text-mist">{s.noZones}</p>
            ) : (
              <ul className="space-y-0.5 text-mist">
                {plan.zones_crossed.map((id) => (
                  <li key={id} className="flex items-start gap-1.5">
                    <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-coral" />
                    <span className="text-foam">{zoneName(id)}</span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          {/* Risk summary */}
          <section>
            <h4 className="mb-1 font-bold text-foam">{s.riskSummary}</h4>
            <p className="text-mist">
              <span className="font-mono text-foam">
                {plan.risk_exposure.toFixed(2)}
              </span>{' '}
              ({riskLevelWord(language, plan.risk_exposure)})
            </p>
          </section>

          {/* Weather window */}
          {plan.weather_window && (
            <section>
              <h4 className="mb-1 font-bold text-foam">{s.weatherWindow}</h4>
              <p className="text-mist">
                {formatLocalShort(plan.weather_window.from)} →{' '}
                {formatLocalShort(plan.weather_window.to)}
                <br />
                <span className="font-mono text-foam">
                  {plan.weather_window.max_wave_m.toFixed(1)} {s.meters}
                </span>{' '}
                ·{' '}
                <span className="font-mono text-foam">
                  {plan.weather_window.max_wind_kn.toFixed(0)} {s.knots}
                </span>
                <br />
                {plan.weather_window.note}
              </p>
            </section>
          )}

          {/* Citations — every claim shows its source; null url -> demo text */}
          <section>
            <h4 className="mb-1 font-bold text-foam">{s.citations}</h4>
            {plan.citations.length === 0 ? (
              <p className="text-mist">{s.bundledDemoData}</p>
            ) : (
              <ul className="space-y-1 text-mist">
                {plan.citations.map((c) => (
                  <li key={c.tool_call_id}>
                    <code className="rounded bg-current/40 px-1 py-0.5 text-[10px] text-surf">
                      [tool:{c.tool}]
                    </code>{' '}
                    <span>{c.claim}</span>{' '}
                    {c.source_url ? (
                      <a
                        href={c.source_url}
                        target="_blank"
                        rel="noreferrer"
                        className="font-semibold text-surf hover:underline"
                      >
                        ↗
                      </a>
                    ) : c.source_label ? (
                      <span className="italic text-mist/70">— {c.source_label}</span>
                    ) : (
                      <span className="italic text-mist/70">({s.bundledDemoData})</span>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </section>

          {/* Agent narrative (plain-language, cited) */}
          {narrative && narrative.length > 0 && recommended && (
            <section>
              <h4 className="mb-1 font-bold text-foam">{s.summary}</h4>
              <ul className="space-y-1 text-mist">
                {narrative.map((n, i) => (
                  <li key={i}>{n.text}</li>
                ))}
              </ul>
            </section>
          )}

          {/* Print brief (Task 5) */}
          <button
            onClick={() => openBrief(plan, language, { zoneName, trip })}
            className="min-h-9 w-full rounded-lg border border-surf/60 px-3 text-xs font-semibold text-surf transition-colors hover:bg-surf/15 focus-visible:ring-2 focus-visible:ring-surf"
          >
            {s.printBrief}
          </button>

          {/* Advisory disclaimer on every plan (Req 9.1) */}
          <p className="border-t border-depth pt-2 text-[10px] leading-snug text-mist/80">
            {DISCLAIMER[language]}
          </p>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-2">
      <dt className="truncate">{label}</dt>
      <dd className="shrink-0 font-mono text-foam">{value}</dd>
    </div>
  );
}
