import { ModeToggle } from './ModeToggle';
import { DemoBadge } from './DemoBadge';
import { formatLocalShort } from '@/lib/time';

interface TopBarProps {
  demoMode: boolean;
  dataTimestamp: string | null;
}

export function TopBar({ demoMode, dataTimestamp }: TopBarProps) {
  return (
    <header className="pointer-events-none absolute inset-x-0 top-0 z-20 flex items-start justify-between gap-3 p-3 sm:p-4">
      {/* Brand + data timestamp strip */}
      <div className="pointer-events-auto flex flex-col gap-1">
        <div className="flex items-center gap-2 rounded-xl border border-depth bg-deep/80 px-3 py-2 backdrop-blur">
          <span className="text-lg font-bold tracking-tight text-foam">Fathom</span>
          <span className="hidden text-xs text-mist sm:inline">
            ocean decision copilot
          </span>
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
        </div>
      </div>

      {/* Mode toggle + demo badge */}
      <div className="pointer-events-auto flex flex-col items-end gap-2">
        <ModeToggle />
        <DemoBadge demoMode={demoMode} />
      </div>
    </header>
  );
}
