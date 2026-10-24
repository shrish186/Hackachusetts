import { useAppState, type LayerToggles } from '@/state/AppState';
import { ZONE_COLORS, ZONE_LABELS } from '@/lib/zones';
import type { ZoneKind } from '@/api/types';

const LAYER_META: { key: keyof LayerToggles; label: string; swatch: string }[] = [
  { key: 'risk', label: 'Whale risk', swatch: '#e5544b' },
  { key: 'zones', label: 'Protection zones', swatch: '#39b7d6' },
  { key: 'conditions', label: 'Sea state (waves)', swatch: '#1b7fa8' },
  { key: 'sightings', label: 'Whale sightings', swatch: '#e6f4f9' },
];

/** Layer toggles + legend (requirements.md Req 1.4). Collapsible on mobile. */
export function LayerPanel() {
  const { layers, toggleLayer, speedKn, setSpeedKn } = useAppState();
  return (
    <div className="pointer-events-auto w-60 rounded-2xl border border-depth bg-deep/85 p-4 backdrop-blur">
      <h2 className="mb-3 text-xs font-bold uppercase tracking-wide text-mist">
        Layers
      </h2>
      <div className="space-y-2">
        {LAYER_META.map((l) => (
          <label
            key={l.key}
            className="flex min-h-9 cursor-pointer items-center gap-2.5 text-sm text-foam"
          >
            <input
              type="checkbox"
              checked={layers[l.key]}
              onChange={() => toggleLayer(l.key)}
              className="h-4 w-4 accent-surf"
            />
            <span
              className="h-3 w-3 rounded-sm"
              style={{ backgroundColor: l.swatch }}
            />
            {l.label}
          </label>
        ))}
      </div>

      {layers.risk && (
        <div className="mt-4 border-t border-depth pt-3">
          <div className="mb-1 flex justify-between text-xs text-mist">
            <span>Planned speed</span>
            <span className="font-mono text-foam">{speedKn} kn</span>
          </div>
          <input
            type="range"
            min={4}
            max={20}
            step={0.5}
            value={speedKn}
            onChange={(e) => setSpeedKn(Number(e.target.value))}
            aria-label="Planned vessel speed (knots)"
            className="h-8 w-full cursor-pointer accent-surf"
          />
          <p className="mt-1 text-[10px] leading-snug text-mist">
            Higher speed raises strike risk (lethality curve).
          </p>

          {/* Risk heatmap legend (item 3) */}
          <div className="mt-3">
            <div className="mb-1 text-[11px] font-semibold text-foam">
              Whale risk (0 to 1)
            </div>
            <div
              className="h-2.5 w-full rounded-full"
              style={{
                background:
                  'linear-gradient(to right, rgba(57,183,214,0.35), #f2994a, #e5544b)',
              }}
              aria-hidden
            />
            <div className="mt-0.5 flex justify-between text-[10px] text-mist">
              <span>0</span>
              <span>0.5</span>
              <span>1</span>
            </div>
          </div>
        </div>
      )}

      <div className="mt-4 border-t border-depth pt-3">
        <h3 className="mb-2 text-[10px] font-bold uppercase tracking-wide text-mist">
          Zone types
        </h3>
        <ul className="space-y-1">
          {(Object.keys(ZONE_LABELS) as ZoneKind[]).map((k) => (
            <li key={k} className="flex items-center gap-2 text-[11px] text-mist">
              <span
                className="h-2.5 w-2.5 rounded-sm"
                style={{ backgroundColor: ZONE_COLORS[k] }}
              />
              {ZONE_LABELS[k]}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
