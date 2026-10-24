import { useState } from 'react';
import type { NarrativeLine } from '@/api/client';
import type { Language, RoutePlan, TripRequest } from '@/api/types';
import { t, riskLevelWord, DISCLAIMER } from '@/lib/i18n';
import { formatLocalShort } from '@/lib/time';
import { openBrief } from '@/lib/brief';

interface PlanCardProps {
  plan: RoutePlan;
  rank: number;
  language: Language;
  selected: boolean;
  onSelect: () => void;
  /** Resolve a zone id to its display name (names stay identical across langs). */
  zoneName: (id: string) => string;
  /** The trip request this plan answers (for the printable brief). */
  trip?: TripRequest;
  /** Agent narrative lines (shown in the "why" drawer when present). */
  narrative?: NarrativeLine[];
}

/**
 * A ranked trip plan card (requirements.md Req 4.1/4.2). Selecting it draws the
 * route on the map. The "Why" drawer shows zones crossed, a risk summary, the
 * weather window, and citations (tasks.md 2.9). The advisory disclaimer shows
 * on every plan (Req 9.1).
 */
export function PlanCard({
  plan,
  rank,
  language,
  selected,
  onSelect,
  zoneName,
  trip,
  narrative,
}: PlanCardProps) {
  const [open, setOpen] = useState(false);
  const s = t(language);

  return (
    <div
      className={[
        'rounded-xl border p-3 transition-colors',
        selected ? 'border-surf bg-surf/10' : 'border-depth bg-abyss/50',
      ].join(' ')}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="min-w-0">
          <span className="text-sm font-bold text-foam">
            {s.option} {rank}
          </span>
          {plan.name && (
            <span className="ml-2 text-[11px] text-mist">{plan.name}</span>
          )}
          {rank === 1 && (
            <span className="ml-2 rounded-full bg-kelp/20 px-2 py-0.5 text-[10px] font-bold text-kelp">
              {s.recommended}
            </span>
          )}
        </div>
        <span className="shrink-0 rounded-full bg-tide/25 px-2 py-0.5 text-xs font-semibold text-surf">
          {s.risk} {plan.risk_exposure.toFixed(2)}
        </span>
      </div>

      <dl className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-xs text-mist">
        <Stat label={s.eta} value={`${plan.eta_hours.toFixed(1)} ${s.hours}`} />
        <Stat label={s.fuelEst} value={`${plan.fuel_est_l.toFixed(0)} ${s.liters}`} />
        <Stat label={s.maxWave} value={`${plan.max_wave_m.toFixed(1)} ${s.meters}`} />
        <Stat label={s.effortEst} value={plan.effort_proxy.toFixed(2)} />
      </dl>

      <div className="mt-3 flex items-center gap-2">
        <button
          onClick={onSelect}
          className={[
            'min-h-9 flex-1 rounded-lg px-3 text-xs font-semibold transition-colors',
            selected
              ? 'bg-surf text-abyss'
              : 'bg-tide text-foam hover:bg-surf',
          ].join(' ')}
        >
          {selected ? s.shownOnMap : s.showOnMap}
        </button>
        <button
          onClick={() => setOpen((o) => !o)}
          aria-expanded={open}
          className="min-h-9 rounded-lg border border-depth px-3 text-xs font-semibold text-mist transition-colors hover:text-foam"
        >
          {open ? s.hide : s.why}
        </button>
      </div>

      {open && (
        <div className="mt-3 space-y-3 border-t border-depth pt-3 text-xs">
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

          {/* Citations */}
          <section>
            <h4 className="mb-1 font-bold text-foam">{s.citations}</h4>
            <ul className="space-y-1 text-mist">
              {plan.citations.map((c) => (
                <li key={c.tool_call_id}>
                  <code className="rounded bg-current/40 px-1 py-0.5 text-[10px] text-surf">
                    [tool:{c.tool}]
                  </code>{' '}
                  <span>{c.claim}</span>
                  {c.source_url ? (
                    <>
                      {' '}
                      <a
                        href={c.source_url}
                        target="_blank"
                        rel="noreferrer"
                        className="font-semibold text-surf hover:underline"
                      >
                        ↗
                      </a>
                    </>
                  ) : (
                    c.source_label && <span className="italic text-mist/70"> — {c.source_label}</span>
                  )}
                </li>
              ))}
            </ul>
          </section>

          {/* Agent narrative (plain-language, cited) */}
          {narrative && narrative.length > 0 && rank === 1 && (
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
            className="min-h-9 w-full rounded-lg border border-surf/60 px-3 text-xs font-semibold text-surf transition-colors hover:bg-surf/15"
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
