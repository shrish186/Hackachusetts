import type { Zone } from '@/api/types';
import { ZONE_LABELS, isZoneActive, restrictionSummary } from '@/lib/zones';
import { formatLocalShort } from '@/lib/time';

interface ZonePopupProps {
  zone: Zone;
  timeIso: string;
  onClose: () => void;
}

/** Zone detail card (requirements.md Req 2.2 / 2.4). */
export function ZonePopup({ zone, timeIso, onClose }: ZonePopupProps) {
  const active = isZoneActive(zone, timeIso);
  return (
    <div className="pointer-events-auto absolute left-1/2 top-24 z-30 w-[min(92vw,22rem)] -translate-x-1/2 rounded-xl border border-depth bg-deep/95 p-4 shadow-2xl backdrop-blur">
      <div className="mb-2 flex items-start justify-between gap-2">
        <div>
          <div className="text-xs uppercase tracking-wide text-mist">
            {ZONE_LABELS[zone.kind]}
          </div>
          <h3 className="text-base font-bold text-foam">{zone.name}</h3>
        </div>
        <button
          onClick={onClose}
          aria-label="Close"
          className="flex h-8 w-8 items-center justify-center rounded-full text-mist hover:bg-current/40 hover:text-foam"
        >
          ✕
        </button>
      </div>

      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span
          className={[
            'rounded-full px-2 py-0.5 font-semibold',
            active ? 'bg-kelp/20 text-kelp' : 'bg-current/40 text-mist',
          ].join(' ')}
        >
          {active ? 'Active now' : 'Inactive at this time'}
        </span>
        {zone.prohibited && (
          <span className="rounded-full bg-alert/20 px-2 py-0.5 font-semibold text-alert">
            No entry
          </span>
        )}
        {zone.synthetic && (
          <span
            className="rounded-full bg-coral/20 px-2 py-0.5 font-semibold text-coral"
            title="This zone is a synthetic / hand-digitized seed, not an official feed."
          >
            synthetic
          </span>
        )}
      </div>

      <p className="mt-3 text-sm text-foam">{restrictionSummary(zone)}</p>

      <dl className="mt-3 space-y-1 text-xs text-mist">
        <div className="flex justify-between gap-3">
          <dt>Effective</dt>
          <dd className="text-right text-foam">
            {zone.active_from ? formatLocalShort(zone.active_from) : '—'}
            {' → '}
            {zone.active_to ? formatLocalShort(zone.active_to) : '—'}
          </dd>
        </div>
        {zone.speed_limit_kn != null && (
          <div className="flex justify-between gap-3">
            <dt>Speed limit</dt>
            <dd className="text-foam">{zone.speed_limit_kn} kn</dd>
          </div>
        )}
        <div className="flex justify-between gap-3">
          <dt>Source updated</dt>
          <dd className="text-foam">{formatLocalShort(zone.source_updated)}</dd>
        </div>
      </dl>

      <a
        href={zone.source_url}
        target="_blank"
        rel="noreferrer"
        className="mt-3 inline-block text-xs font-semibold text-surf hover:underline"
      >
        View source notice →
      </a>
    </div>
  );
}
