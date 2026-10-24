import { useEffect, useRef, useState } from 'react';
import { pingHealth } from '@/api/client';
import { useConn } from '@/hooks/useConn';

/**
 * Cold-start / offline UX (task 7).
 *
 * - On mount, pings the backend health endpoint (free-tier servers can take up
 *   to ~60 s to wake). While waiting, shows "Waking the server…".
 * - If unreachable, shows "Showing sample data, live server unreachable" with a
 *   Retry button, and auto-retries every 20 s for up to 3 minutes.
 * - Disappears once a real response arrives (conn === 'online').
 */
const RETRY_INTERVAL_MS = 20_000;
const MAX_AUTO_RETRY_MS = 180_000;

export function OfflineBanner() {
  const conn = useConn();
  const [retrying, setRetrying] = useState(false);
  const startedAt = useRef<number>(Date.now());
  const timerRef = useRef<number | null>(null);

  async function retry() {
    setRetrying(true);
    try {
      await pingHealth();
    } finally {
      setRetrying(false);
    }
  }

  // Initial probe on mount.
  useEffect(() => {
    startedAt.current = Date.now();
    void retry();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Auto-retry loop while offline, capped at 3 minutes.
  useEffect(() => {
    if (conn === 'online') {
      if (timerRef.current) window.clearInterval(timerRef.current);
      return;
    }
    timerRef.current = window.setInterval(() => {
      if (Date.now() - startedAt.current > MAX_AUTO_RETRY_MS) {
        if (timerRef.current) window.clearInterval(timerRef.current);
        return;
      }
      if (conn === 'offline') void retry();
    }, RETRY_INTERVAL_MS);
    return () => {
      if (timerRef.current) window.clearInterval(timerRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conn]);

  if (conn === 'online') return null;

  const waking = conn === 'waking' || retrying;

  return (
    <div
      role="status"
      aria-live="polite"
      className="pointer-events-auto flex items-center gap-3 rounded-xl border border-coral/50 bg-coral/15 px-3 py-2 text-xs text-coral backdrop-blur"
    >
      {waking ? (
        <>
          <span className="h-3 w-3 shrink-0 animate-spin rounded-full border-2 border-coral border-t-transparent" />
          <span className="font-semibold">Waking the server (free tier, up to 60 s)…</span>
        </>
      ) : (
        <>
          <span className="shrink-0 text-sm">⚠</span>
          <span className="font-semibold">Showing sample data, live server unreachable</span>
          <button
            onClick={retry}
            className="ml-auto shrink-0 rounded-md border border-coral/60 px-2 py-1 font-bold text-coral transition-colors hover:bg-coral/20 focus-visible:ring-2 focus-visible:ring-coral"
          >
            Retry
          </button>
        </>
      )}
    </div>
  );
}
