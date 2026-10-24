import { useAppState, type Mode } from '@/state/AppState';

const MODES: { id: Mode; label: string; hint: string }[] = [
  { id: 'captain', label: 'Captain', hint: 'Plan a trip' },
  { id: 'manager', label: 'Manager', hint: 'What-if simulator' },
];

export function ModeToggle() {
  const { mode, setMode } = useAppState();
  return (
    <div
      role="tablist"
      aria-label="Mode"
      className="flex rounded-full border border-depth bg-deep/80 p-1 backdrop-blur"
    >
      {MODES.map((m) => {
        const active = mode === m.id;
        return (
          <button
            key={m.id}
            role="tab"
            aria-selected={active}
            title={m.hint}
            onClick={() => setMode(m.id)}
            className={[
              'min-h-10 rounded-full px-4 text-sm font-semibold transition-colors',
              active
                ? 'bg-tide text-foam shadow'
                : 'text-mist hover:text-foam',
            ].join(' ')}
          >
            {m.label}
          </button>
        );
      })}
    </div>
  );
}
