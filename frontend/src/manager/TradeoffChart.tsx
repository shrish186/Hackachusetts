import type { ScenarioResult } from '@/api/types';

interface TradeoffChartProps {
  scenarios: ScenarioResult[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  labels: { xAxis: string; yAxis: string; frontier: string };
}

/**
 * Hand-rolled SVG scatter of whale risk reduced (x) vs fleet livelihood cost
 * (y), one dot per scenario (requirements.md Req 6.2/6.3). Efficient-frontier
 * options are highlighted and labeled. No chart library.
 *
 * Axes (both "more is worse to the top-right is better bottom-right"):
 *   x = risk reduced %  = -delta_risk_pct  (higher is better)
 *   y = fleet cost %    = avg(added hours%, -effort access%) (lower is better)
 */
export function TradeoffChart({ scenarios, selectedId, onSelect, labels }: TradeoffChartProps) {
  const W = 300;
  const H = 210;
  const pad = { l: 38, r: 12, t: 12, b: 34 };
  const plotW = W - pad.l - pad.r;
  const plotH = H - pad.t - pad.b;

  const pts = scenarios.map((s) => ({
    s,
    riskReduced: -s.delta_risk_pct, // higher = more risk removed
    fleetCost: (s.delta_hours_pct + -s.delta_effort_access_pct) / 2, // higher = costlier
  }));

  const xMax = Math.max(10, ...pts.map((p) => p.riskReduced)) * 1.1;
  const yMax = Math.max(10, ...pts.map((p) => p.fleetCost)) * 1.15;

  const sx = (v: number) => pad.l + (v / xMax) * plotW;
  const sy = (v: number) => pad.t + plotH - (v / yMax) * plotH;

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      className="w-full"
      role="img"
      aria-label={`Trade-off chart: ${labels.xAxis} versus ${labels.yAxis}`}
    >
      {/* grid */}
      {[0.25, 0.5, 0.75, 1].map((f) => (
        <line
          key={f}
          x1={pad.l}
          x2={pad.l + plotW}
          y1={pad.t + plotH - f * plotH}
          y2={pad.t + plotH - f * plotH}
          stroke="#0e3a56"
          strokeWidth={1}
        />
      ))}
      {/* axes */}
      <line x1={pad.l} y1={pad.t} x2={pad.l} y2={pad.t + plotH} stroke="#12506f" />
      <line x1={pad.l} y1={pad.t + plotH} x2={pad.l + plotW} y2={pad.t + plotH} stroke="#12506f" />

      {/* axis labels */}
      <text x={pad.l + plotW / 2} y={H - 6} textAnchor="middle" fontSize="9" fill="#9bc3d4">
        {labels.xAxis} →
      </text>
      <text
        x={10}
        y={pad.t + plotH / 2}
        textAnchor="middle"
        fontSize="9"
        fill="#9bc3d4"
        transform={`rotate(-90 10 ${pad.t + plotH / 2})`}
      >
        {labels.yAxis} →
      </text>

      {/* points */}
      {pts.map(({ s, riskReduced, fleetCost }) => {
        const cx = sx(riskReduced);
        const cy = sy(fleetCost);
        const isSel = s.scenario_id === selectedId;
        const fill = s.on_frontier ? '#3fae8f' : '#1b7fa8';
        return (
          <g key={s.scenario_id} className="cursor-pointer" onClick={() => onSelect(s.scenario_id)}>
            {s.on_frontier && (
              <circle cx={cx} cy={cy} r={isSel ? 11 : 9} fill="none" stroke="#3fae8f" strokeWidth={1.5} opacity={0.6} />
            )}
            <circle cx={cx} cy={cy} r={isSel ? 7 : 5} fill={fill} stroke="#e6f4f9" strokeWidth={isSel ? 2 : 1} />
            <text x={cx} y={cy - 12} textAnchor="middle" fontSize="8" fill="#e6f4f9">
              {Math.round(riskReduced)}%
            </text>
          </g>
        );
      })}

      {/* frontier legend */}
      <g>
        <circle cx={pad.l + 6} cy={pad.t + 6} r={4} fill="#3fae8f" />
        <text x={pad.l + 14} y={pad.t + 9} fontSize="8" fill="#9bc3d4">
          {labels.frontier}
        </text>
      </g>
    </svg>
  );
}
