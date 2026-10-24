import type { Language, RoutePlan } from '@/api/types';
import type { PlanClass } from '@/lib/recommend';
import { planClassLabel, t } from '@/lib/i18n';

interface PlanComparisonChartProps {
  plans: RoutePlan[];
  planClasses: PlanClass[];
  recommendedIdx: number;
  /** Index of the highlighted plan (selected or hovered), or null. */
  activeIdx: number | null;
  onHover: (i: number | null) => void;
  onSelect: (i: number) => void;
  language: Language;
}

/**
 * Small SVG scatter comparing plans (item 3): x = ETA hours, y = whale risk.
 * One dot per plan, labelled Fastest/Balanced/Safest/Alternative; the
 * recommended plan is ringed. Hover/tap highlights the dot (and, via the
 * parent, its card + route on the map). No chart library — matches the
 * Manager TradeoffChart style.
 */
export function PlanComparisonChart({
  plans,
  planClasses,
  recommendedIdx,
  activeIdx,
  onHover,
  onSelect,
  language,
}: PlanComparisonChartProps) {
  const s = t(language);
  if (plans.length < 2) return null;

  const W = 300;
  const H = 150;
  const pad = { l: 40, r: 14, t: 12, b: 30 };
  const plotW = W - pad.l - pad.r;
  const plotH = H - pad.t - pad.b;

  const etas = plans.map((p) => p.eta_hours);
  const risks = plans.map((p) => p.risk_exposure);
  const xMin = Math.min(...etas);
  const xMax = Math.max(...etas);
  const yMin = Math.min(...risks);
  const yMax = Math.max(...risks);

  const sx = (v: number) =>
    pad.l + (xMax === xMin ? 0.5 : (v - xMin) / (xMax - xMin)) * plotW;
  const sy = (v: number) =>
    pad.t + plotH - (yMax === yMin ? 0.5 : (v - yMin) / (yMax - yMin)) * plotH;

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      className="w-full"
      role="img"
      aria-label={`${s.eta} vs ${s.riskSummary}`}
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
      <line x1={pad.l} y1={pad.t} x2={pad.l} y2={pad.t + plotH} stroke="#12506f" />
      <line x1={pad.l} y1={pad.t + plotH} x2={pad.l + plotW} y2={pad.t + plotH} stroke="#12506f" />

      {/* axis labels */}
      <text x={pad.l + plotW / 2} y={H - 4} textAnchor="middle" fontSize="9" fill="#9bc3d4">
        {s.eta} ({s.hours}) →
      </text>
      <text
        x={11}
        y={pad.t + plotH / 2}
        textAnchor="middle"
        fontSize="9"
        fill="#9bc3d4"
        transform={`rotate(-90 11 ${pad.t + plotH / 2})`}
      >
        {s.riskSummary} ↑
      </text>

      {plans.map((p, i) => {
        const cx = sx(p.eta_hours);
        const cy = sy(p.risk_exposure);
        const isActive = i === activeIdx;
        const isRec = i === recommendedIdx;
        return (
          <g
            key={i}
            className="cursor-pointer"
            onMouseEnter={() => onHover(i)}
            onMouseLeave={() => onHover(null)}
            onClick={() => onSelect(i)}
            role="button"
            aria-label={planClassLabel(language, planClasses[i])}
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onSelect(i);
              }
            }}
          >
            {isRec && (
              <circle cx={cx} cy={cy} r={isActive ? 10 : 8} fill="none" stroke="#3fae8f" strokeWidth={1.5} opacity={0.8} />
            )}
            <circle
              cx={cx}
              cy={cy}
              r={isActive ? 6 : 4.5}
              fill={isActive ? '#39b7d6' : '#1b7fa8'}
              stroke="#e6f4f9"
              strokeWidth={isActive ? 2 : 1}
            />
            <text x={cx} y={cy - 9} textAnchor="middle" fontSize="7.5" fill="#e6f4f9">
              {planClassLabel(language, planClasses[i])}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
