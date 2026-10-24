interface DemoBadgeProps {
  show: boolean;
}

/**
 * "Demo data" badge, shown when the app is running on bundled snapshots / mocks
 * (requirements.md Req 10.2). Visible, not hidden.
 */
export function DemoBadge({ show }: DemoBadgeProps) {
  if (!show) return null;
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full border border-coral/50 bg-coral/15 px-3 py-1 text-xs font-semibold tracking-wide text-coral"
      title="The app is running on bundled demo data, not a live feed."
    >
      <span className="h-1.5 w-1.5 rounded-full bg-coral" />
      Demo data
    </span>
  );
}
