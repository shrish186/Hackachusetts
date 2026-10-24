import { useEffect, useRef } from 'react';
import { pingHealth } from '@/api/client';
import { useConn } from '@/hooks/useConn';
import { useAppState } from '@/state/AppState';
import { t } from '@/lib/i18n';

/**
 * Cold-start / offline UX (item 4).
 *
 * Free-tier servers can take up to ~60 s to wake. For the first 60 s of failed
 * calls the connection state stays "waking" (the client tracks the window), so
 * we show a NEUTRAL "Waking the server…" pill — never the red offline badge.
 * We re-probe GET /api/health every 5 s and switch to Live automatically when
 * it answers. Only after 60 s of continuous failures does the client flip to
 * "offline" and we show the red banner with a working Retry button.
 */
const RETRY_INTERVAL_MS = 5_000;

export function OfflineBanner() {
  const conn = useConn();
  const { language } = useAppState();
  const s = t(language);
  const timerRef = useRef<number | null>(null);

  async function retry() {
    await pingHealth();
  }

  // Initial probe on mount.
  useEffect(() => {
    void retry();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Re-probe every 5 s until we're online (covers both waking and offline).
  useEffect(() => {
    if (conn === 'online') {
      if (timerRef.current) window.clearInterval(timerRef.current);
      return;
    }
    timerRef.current = window.setInterval(() => void retry(), RETRY_INTERVAL_MS);
    return () => {
      if (timerRef.current) window.clearInterval(timerRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conn]);

  if (conn === 'online') return null;

  // "waking" (first 60 s): neutral pill. "offline" (>60 s): red + Retry.
  if (conn === 'waking' || conn === 'unknown') {
    return (
      <div
        role="status"
        aria-live="polite"
        className="pointer-events-auto flex items-center gap-2 rounded-xl border border-depth bg-deep/80 px-3 py-2 text-xs text-mist backdrop-blur"
      >
        <span className="h-3 w-3 shrink-0 animate-spin rounded-full border-2 border-surf border-t-transparent" />
        <span className="font-semibold">{s.wakingServer}</span>
      </div>
    );
  }

  return (
    <div
      role="status"
      aria-live="polite"
      className="pointer-events-auto flex items-center gap-3 rounded-xl border border-alert/50 bg-alert/15 px-3 py-2 text-xs text-alert backdrop-blur"
    >
      <span className="shrink-0 text-sm" aria-hidden>⚠</span>
      <span className="font-semibold">{s.offlineDemo}</span>
      <button
        onClick={() => void retry()}
        className="ml-auto shrink-0 rounded-md border border-alert/60 px-2 py-1 font-bold text-alert transition-colors hover:bg-alert/20 focus-visible:ring-2 focus-visible:ring-alert"
      >
        {s.retry}
      </button>
    </div>
  );
}
