import type { Ground } from '@/api/types';
import type { Language } from '@/api/types';
import { t } from '@/lib/i18n';

const MONTH = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', timeZone: 'UTC' });

/** "1 Feb–30 Apr" from ISO dates, or '' if unknown. */
export function closedRange(g: Ground): string {
  if (!g.closed_from || !g.closed_to) return '';
  return `${MONTH.format(new Date(g.closed_from))}–${MONTH.format(new Date(g.closed_to))}`;
}

/**
 * Red "Closed …" chip for a closed ground (item 2). Carries a lock glyph and
 * the word "Closed" so meaning is not color-only (item 7). The zone name is in
 * the title tooltip.
 */
export function ClosedChip({ ground, language }: { ground: Ground; language: Language }) {
  const s = t(language);
  const range = closedRange(ground);
  return (
    <span
      title={ground.closed_reason ?? undefined}
      className="inline-flex items-center gap-1 rounded-full border border-alert/60 bg-alert/15 px-2 py-0.5 text-[10px] font-bold text-alert"
    >
      <span aria-hidden>🔒</span>
      {s.closedPrefix}
      {range ? ` ${range}` : ''}
    </span>
  );
}
