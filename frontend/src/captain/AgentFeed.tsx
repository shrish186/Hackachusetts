import type { AgentEvent, Language } from '@/api/types';
import { t } from '@/lib/i18n';

interface AgentFeedProps {
  events: AgentEvent[];
  language: Language;
  active: boolean;
}

/**
 * Live feed of the agent's tool calls, shown one by one (requirements.md
 * Req 4.5; design.md §7). Each step shows a spinner while running and a check
 * with a one-line result when done. Lets the captain see what was checked.
 */
export function AgentFeed({ events, language, active }: AgentFeedProps) {
  const s = t(language);
  if (events.length === 0) return null;

  return (
    <div className="rounded-xl border border-depth bg-abyss/50 p-3">
      <h3 className="mb-2 flex items-center gap-2 text-[11px] font-bold uppercase tracking-wide text-mist">
        {active && (
          <span className="h-2 w-2 animate-pulse rounded-full bg-surf" aria-hidden />
        )}
        {s.agentFeedTitle}
      </h3>
      <ol className="space-y-1.5">
        {events.map((e) => (
          <li key={e.id} className="flex items-start gap-2 text-xs">
            <span className="mt-0.5 shrink-0" aria-hidden>
              {e.status === 'running' ? (
                <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-surf border-t-transparent" />
              ) : e.status === 'error' ? (
                <span className="text-alert">✕</span>
              ) : (
                <span className="text-kelp">✓</span>
              )}
            </span>
            <span className="min-w-0">
              <span className="text-foam">{e.label}</span>
              {e.detail && e.status === 'done' && (
                <span className="block text-[11px] leading-snug text-mist">
                  {e.detail}{' '}
                  <code className="rounded bg-current/40 px-1 py-0.5 text-[10px] text-surf">
                    [tool:{e.tool}]
                  </code>
                </span>
              )}
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}
