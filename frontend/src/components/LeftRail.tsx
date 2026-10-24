import { ReplayToggle } from './ReplayToggle';
import { formatLocalShort } from '@/lib/time';
import { useAppState } from '@/state/AppState';
import { t } from '@/lib/i18n';
import { navigate } from '@/lib/router';

interface LeftRailProps {
  dataTimestamp: string | null;
  onOpenSources: () => void;
}

/**
 * The left-column header stack (item 2): brand, data-timestamp / Sources /
 * About row, the Today / Replay toggle, and the replay banner — in a vertical
 * flex column. App renders the planner panel directly beneath this stack so
 * the banner can never overlap the "Plan a trip" title at any size or language.
 */
export function LeftRail({ dataTimestamp, onOpenSources }: LeftRailProps) {
  const { replay, language } = useAppState();
  const s = t(language);
  return (
    <div className="flex flex-col gap-1">
      <div className="flex w-max items-center gap-2 rounded-xl border border-depth bg-deep/80 px-3 py-2 backdrop-blur">
        <span className="text-lg font-bold tracking-tight text-foam">Fathom</span>
        <span className="hidden text-xs text-mist sm:inline">ocean decision copilot</span>
      </div>
      <div className="flex flex-wrap items-center gap-2 text-xs text-mist">
        {dataTimestamp && (
          <span
            className="rounded-md border border-depth bg-deep/70 px-2 py-1 backdrop-blur"
            title="Latest data timestamp (America/New_York)"
          >
            Data as of {formatLocalShort(dataTimestamp)}
          </span>
        )}
        <button
          onClick={onOpenSources}
          className="rounded-md border border-depth bg-deep/70 px-2 py-1 font-semibold text-surf backdrop-blur transition-colors hover:text-foam focus-visible:ring-2 focus-visible:ring-surf"
          title="Show data sources and their timestamps"
        >
          Sources
        </button>
        <a
          href="/about"
          onClick={(e) => {
            e.preventDefault();
            navigate('/about');
          }}
          className="rounded-md border border-depth bg-deep/70 px-2 py-1 font-semibold text-surf backdrop-blur transition-colors hover:text-foam focus-visible:ring-2 focus-visible:ring-surf"
        >
          {s.about}
        </a>
      </div>

      {/* Today / Replay whale season toggle */}
      <ReplayToggle />

      {/* Replay banner — part of the stack, so it pushes the planner down */}
      {replay && (
        <div
          role="status"
          className="w-max max-w-xs rounded-md border border-surf/50 bg-surf/15 px-2 py-1 text-[11px] font-semibold text-surf backdrop-blur"
        >
          {s.replayBanner}
        </div>
      )}
    </div>
  );
}
