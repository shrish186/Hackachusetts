import { useAppState } from '@/state/AppState';
import { t } from '@/lib/i18n';

/**
 * "Today" / "Replay whale season (15 Mar 2026)" toggle (item 1).
 *
 * When replay is on, every layer fetch uses the whale-season instant
 * (2026-03-15T13:00:00Z) so the map shows active closures, the time slider
 * snaps to that date, and the Captain departure defaults to it. A small banner
 * elsewhere states the replay is active.
 */
export function ReplayToggle() {
  const { replay, setReplay, language } = useAppState();
  const s = t(language);

  return (
    <div
      role="group"
      aria-label={s.replayWhaleSeason}
      className="flex overflow-hidden rounded-lg border border-depth bg-deep/80 text-[11px] font-semibold backdrop-blur"
    >
      <button
        onClick={() => setReplay(false)}
        aria-pressed={!replay}
        className={[
          'px-2.5 py-1.5 transition-colors focus-visible:ring-2 focus-visible:ring-surf',
          !replay ? 'bg-tide text-foam' : 'text-mist hover:text-foam',
        ].join(' ')}
      >
        {s.today}
      </button>
      <button
        onClick={() => setReplay(true)}
        aria-pressed={replay}
        title={s.replayWhaleSeason}
        className={[
          'px-2.5 py-1.5 transition-colors focus-visible:ring-2 focus-visible:ring-surf',
          replay ? 'bg-tide text-foam' : 'text-mist hover:text-foam',
        ].join(' ')}
      >
        {s.replayWhaleSeason}
      </button>
    </div>
  );
}
