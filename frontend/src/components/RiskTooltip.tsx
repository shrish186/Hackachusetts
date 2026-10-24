import type { RiskCell } from '@/api/types';

interface RiskTooltipProps {
  cell: RiskCell;
  x: number;
  y: number;
}

/** Per-cell risk factor breakdown on hover (requirements.md Req 3.4). */
export function RiskTooltip({ cell, x, y }: RiskTooltipProps) {
  return (
    <div
      className="pointer-events-none fixed z-40 w-52 rounded-lg border border-depth bg-abyss/95 p-3 text-xs shadow-xl backdrop-blur"
      style={{ left: x + 14, top: y + 14 }}
    >
      <div className="mb-1 flex items-center justify-between">
        <span className="font-semibold text-foam">Whale risk</span>
        <span className="font-mono text-surf">{cell.risk.toFixed(2)}</span>
      </div>
      <Bar label="Seasonal presence" value={cell.factors.presence} />
      <Bar label="Recent sightings" value={cell.factors.recency} />
      <Bar label="Speed lethality" value={cell.factors.lethality} />
      <p className="mt-2 text-[10px] leading-snug text-mist">
        Synthetic estimate for the demo. Advisory only.
      </p>
    </div>
  );
}

function Bar({ label, value }: { label: string; value: number }) {
  return (
    <div className="mb-1.5">
      <div className="flex justify-between text-mist">
        <span>{label}</span>
        <span className="font-mono">{value.toFixed(2)}</span>
      </div>
      <div className="mt-0.5 h-1.5 w-full overflow-hidden rounded-full bg-current/40">
        <div
          className="h-full rounded-full bg-surf"
          style={{ width: `${Math.round(Math.min(1, value) * 100)}%` }}
        />
      </div>
    </div>
  );
}
