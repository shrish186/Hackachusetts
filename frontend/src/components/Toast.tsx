import { useEffect } from 'react';

interface ToastProps {
  message: string | null;
  onDone: () => void;
  /** ms before auto-dismiss. */
  duration?: number;
}

/** Small transient toast, bottom-center (item 4 "Copy link"). */
export function Toast({ message, onDone, duration = 2200 }: ToastProps) {
  useEffect(() => {
    if (!message) return;
    const id = window.setTimeout(onDone, duration);
    return () => window.clearTimeout(id);
  }, [message, duration, onDone]);

  if (!message) return null;
  return (
    <div
      role="status"
      aria-live="polite"
      className="pointer-events-none fixed bottom-6 left-1/2 z-50 -translate-x-1/2 rounded-full border border-depth bg-deep/95 px-4 py-2 text-sm font-semibold text-foam shadow-2xl backdrop-blur"
    >
      ✓ {message}
    </div>
  );
}
