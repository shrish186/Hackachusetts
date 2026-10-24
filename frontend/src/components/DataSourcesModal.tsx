import { useEffect, useState } from 'react';
import { api } from '@/api/client';
import type { MetaResponse, SourceMeta } from '@/api/types';
import { formatLocalShort } from '@/lib/time';

interface DataSourcesModalProps {
  open: boolean;
  onClose: () => void;
}

/**
 * Data sources modal (tasks.md task 6; requirements.md Req 2.4 / 10.2).
 * Lists every layer from /api/meta/sources with a live / cached / synthetic
 * badge and its timestamp, so provenance is always inspectable.
 */
export function DataSourcesModal({ open, onClose }: DataSourcesModalProps) {
  const [meta, setMeta] = useState<MetaResponse | null>(null);

  useEffect(() => {
    if (!open) return;
    let alive = true;
    api.getMeta().then((m) => alive && setMeta(m));
    return () => {
      alive = false;
    };
  }, [open]);

  // Close on Escape.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-label="Data sources"
    >
      <div className="absolute inset-0 bg-abyss/70 backdrop-blur-sm" onClick={onClose} />
      <div className="relative z-10 max-h-[80vh] w-[min(92vw,34rem)] overflow-y-auto rounded-2xl border border-depth bg-deep p-5 shadow-2xl">
        <div className="mb-3 flex items-start justify-between">
          <div>
            <h2 className="text-base font-bold text-foam">Data sources</h2>
            <p className="text-xs text-mist">
              {meta?.demo_mode
                ? 'Running in demo mode on bundled snapshots.'
                : 'Live source provenance.'}
            </p>
          </div>
          <button
            onClick={onClose}
            aria-label="Close"
            className="flex h-9 w-9 items-center justify-center rounded-full text-mist hover:bg-current/40 hover:text-foam focus-visible:ring-2 focus-visible:ring-surf"
          >
            ✕
          </button>
        </div>

        {!meta ? (
          <div className="space-y-2">
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className="h-12 w-full animate-pulse rounded-lg bg-current/20" />
            ))}
          </div>
        ) : (
          <ul className="space-y-2">
            {meta.sources.map((src) => (
              <SourceRow key={src.layer} src={src} />
            ))}
          </ul>
        )}

        <p className="mt-4 border-t border-depth pt-3 text-[10px] leading-snug text-mist/80">
          Advisory only. Public or synthetic data. Effort proxy is an estimate,
          not catch or revenue.
        </p>
      </div>
    </div>
  );
}

function SourceRow({ src }: { src: SourceMeta }) {
  return (
    <li className="flex items-start justify-between gap-3 rounded-lg border border-depth bg-abyss/40 p-3">
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-foam">{src.layer}</span>
          <ProvenanceBadge src={src} />
        </div>
        {src.source_url ? (
          <a
            href={src.source_url}
            target="_blank"
            rel="noreferrer"
            className="block truncate text-[11px] text-surf hover:underline"
          >
            {src.source_url}
          </a>
        ) : (
          <span className="block text-[11px] text-mist">no source link</span>
        )}
      </div>
      <span className="shrink-0 text-right text-[11px] text-mist">
        {src.fetched_at ? formatLocalShort(src.fetched_at) : '—'}
      </span>
    </li>
  );
}

function ProvenanceBadge({ src }: { src: SourceMeta }) {
  // Synthetic takes precedence (honesty), then cached, else live.
  const kind = src.synthetic ? 'synthetic' : src.cached ? 'cached' : 'live';
  const styles: Record<string, string> = {
    synthetic: 'border-coral/50 bg-coral/15 text-coral',
    cached: 'border-tide/50 bg-tide/15 text-surf',
    live: 'border-kelp/50 bg-kelp/15 text-kelp',
  };
  return (
    <span
      className={`rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide ${styles[kind]}`}
    >
      {kind}
    </span>
  );
}
