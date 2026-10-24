import { useConn } from '@/hooks/useConn';

interface DemoBadgeProps {
  /** True when the backend reports demo mode (bundled snapshots). */
  demoMode: boolean;
}

/**
 * Connection / data-provenance badge (requirements.md Req 10.2).
 *
 * - API unreachable (offline): red "Offline demo data" — we fell back to the
 *   bundled mocks in the browser.
 * - API up but in demo mode: amber "Demo data" — snapshots, not a live feed.
 * - API up, not demo: green "Live API".
 * Always visible so users never mistake demo data for live data.
 */
export function DemoBadge({ demoMode }: DemoBadgeProps) {
  const conn = useConn();

  if (conn === 'offline') {
    return (
      <Badge
        tone="alert"
        label="Offline demo data"
        title="The backend is unreachable. Showing bundled demo data generated in your browser."
      />
    );
  }
  if (conn === 'waking') {
    // Neutral during the cold-start grace window — never the red offline badge.
    return (
      <Badge tone="mist" label="Waking server…" title="Waking the free-tier server (up to 60 s)." />
    );
  }
  if (demoMode) {
    return (
      <Badge
        tone="coral"
        label="Demo data"
        title="Connected to the API in demo mode — bundled snapshots, not a live feed."
      />
    );
  }
  if (conn === 'online') {
    return <Badge tone="kelp" label="Live API" title="Connected to the live Fathom API." />;
  }
  // Unknown (first paint) — stay quiet until the first request resolves.
  return null;
}

function Badge({
  tone,
  label,
  title,
}: {
  tone: 'alert' | 'coral' | 'kelp' | 'mist';
  label: string;
  title: string;
}) {
  const tones: Record<string, string> = {
    alert: 'border-alert/50 bg-alert/15 text-alert',
    coral: 'border-coral/50 bg-coral/15 text-coral',
    kelp: 'border-kelp/50 bg-kelp/15 text-kelp',
    mist: 'border-depth bg-deep/80 text-mist',
  };
  const dot: Record<string, string> = {
    alert: 'bg-alert',
    coral: 'bg-coral',
    kelp: 'bg-kelp',
    mist: 'bg-mist',
  };
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold tracking-wide ${tones[tone]}`}
      title={title}
      role="status"
    >
      <span className={`h-1.5 w-1.5 rounded-full ${dot[tone]}`} />
      {label}
    </span>
  );
}
