import { ModeToggle } from './ModeToggle';
import { DemoBadge } from './DemoBadge';

interface TopBarProps {
  demoMode: boolean;
}

/**
 * Top-right controls only (mode toggle + data badge). The left-column header
 * now lives in <LeftRail/> so it stacks vertically with the planner and never
 * overlaps it (item 2).
 */
export function TopBar({ demoMode }: TopBarProps) {
  return (
    <div className="pointer-events-none absolute right-3 top-3 z-20 flex flex-col items-end gap-2 sm:right-4 sm:top-4">
      <div className="pointer-events-auto flex flex-col items-end gap-2">
        <ModeToggle />
        <DemoBadge demoMode={demoMode} />
      </div>
    </div>
  );
}
