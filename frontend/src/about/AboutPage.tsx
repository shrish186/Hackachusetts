import { useEffect, useState } from 'react';
import type { MetaResponse } from '@/api/types';
import { api } from '@/api/client';
import { useAppState } from '@/state/AppState';
import { t } from '@/lib/i18n';
import { formatLocalShort } from '@/lib/time';
import { navigate } from '@/lib/router';
import { LanguageSwitch } from '@/components/LanguageSwitch';

const KIRO_BASE = 'https://github.com/shrish186/Hackachusetts/tree/main/.kiro';
const KIRO_LINKS: { label: string; href: string }[] = [
  { label: 'specs', href: `${KIRO_BASE}/specs/fathom` },
  { label: 'steering', href: `${KIRO_BASE}/steering` },
  { label: 'hooks', href: `${KIRO_BASE}/hooks` },
  { label: 'MCP', href: 'https://github.com/shrish186/Hackachusetts/tree/main/mcp' },
  { label: 'property tests', href: 'https://github.com/shrish186/Hackachusetts/tree/main/backend/tests' },
];

const TEAM = ['Shrish', 'Anant', 'Vidhaan', 'Aayush'];

/**
 * About / evidence page (item 5). Client-side route at /about with sections:
 * what Fathom does, data sources (live from /api/meta/sources), how we used
 * Kiro (links to the .kiro folders), limits, and the team. EN/PT/ES.
 */
export function AboutPage() {
  const { language, setLanguage } = useAppState();
  const s = t(language);
  const [meta, setMeta] = useState<MetaResponse | null>(null);

  useEffect(() => {
    let alive = true;
    api.getMeta().then((m) => alive && setMeta(m));
    document.title = 'Fathom — About';
    return () => {
      alive = false;
    };
  }, []);

  return (
    <div className="min-h-dvh w-full overflow-y-auto bg-abyss text-foam">
      <div className="mx-auto max-w-3xl px-5 py-8">
        <header className="mb-6 flex items-center justify-between gap-3">
          <button
            onClick={() => navigate('/')}
            className="rounded-lg border border-depth bg-deep px-3 py-2 text-sm font-semibold text-surf transition-colors hover:text-foam focus-visible:ring-2 focus-visible:ring-surf"
          >
            ← {s.aboutBack}
          </button>
          <div className="w-28">
            <LanguageSwitch value={language} onChange={setLanguage} />
          </div>
        </header>

        <h1 className="text-2xl font-bold">Fathom</h1>
        <p className="text-sm text-mist">ocean decision copilot</p>

        <Section title={s.aboutWhatTitle}>
          <p className="leading-relaxed text-mist">{s.aboutWhatBody}</p>
        </Section>

        <Section title={s.aboutDataTitle}>
          {!meta ? (
            <div className="space-y-2">
              {[0, 1, 2, 3].map((i) => (
                <div key={i} className="h-5 w-full animate-pulse rounded bg-current/20" />
              ))}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-xs">
                <thead>
                  <tr className="border-b border-depth text-left text-mist">
                    <th className="py-2 pr-3">{s.colLayer}</th>
                    <th className="py-2 pr-3">{s.colSource}</th>
                    <th className="py-2 pr-3">{s.colKind}</th>
                    <th className="py-2 pr-3">{s.colFetched}</th>
                    <th className="py-2">{s.colLicense}</th>
                  </tr>
                </thead>
                <tbody>
                  {meta.sources.map((src) => {
                    const o = src as typeof src & { name?: string; license?: string };
                    return (
                      <tr key={src.layer} className="border-b border-depth/60 align-top">
                        <td className="py-2 pr-3 font-semibold text-foam">{src.layer}</td>
                        <td className="py-2 pr-3 text-mist">
                          {src.source_url ? (
                            <a
                              href={src.source_url}
                              target="_blank"
                              rel="noreferrer"
                              className="text-surf hover:underline"
                            >
                              {o.name ?? src.source_url}
                            </a>
                          ) : (
                            (o.name ?? '—')
                          )}
                        </td>
                        <td className="py-2 pr-3">
                          {src.synthetic ? (
                            <span className="rounded-full border border-coral/50 bg-coral/15 px-2 py-0.5 font-semibold text-coral">
                              ⚙ {s.synthetic}
                            </span>
                          ) : (
                            <span className="rounded-full border border-kelp/50 bg-kelp/15 px-2 py-0.5 font-semibold text-kelp">
                              ✓ {s.real}
                            </span>
                          )}
                        </td>
                        <td className="py-2 pr-3 text-mist">
                          {src.fetched_at ? formatLocalShort(src.fetched_at) : '—'}
                        </td>
                        <td className="py-2 text-mist">{o.license ?? '—'}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Section>

        <Section title={s.aboutKiroTitle}>
          <p className="leading-relaxed text-mist">{s.aboutKiroBody}</p>
          <ul className="mt-3 flex flex-wrap gap-2">
            {KIRO_LINKS.map((l) => (
              <li key={l.label}>
                <a
                  href={l.href}
                  target="_blank"
                  rel="noreferrer"
                  className="rounded-lg border border-depth bg-deep px-3 py-1.5 text-xs font-semibold text-surf transition-colors hover:text-foam focus-visible:ring-2 focus-visible:ring-surf"
                >
                  {l.label} ↗
                </a>
              </li>
            ))}
          </ul>
        </Section>

        <Section title={s.aboutLimitsTitle}>
          <p className="leading-relaxed text-mist">{s.aboutLimitsBody}</p>
        </Section>

        <Section title={s.aboutTeamTitle}>
          <ul className="flex flex-wrap gap-2">
            {TEAM.map((m) => (
              <li
                key={m}
                className="rounded-full border border-depth bg-deep px-3 py-1 text-sm text-foam"
              >
                {m}
              </li>
            ))}
          </ul>
        </Section>

        <p className="mt-8 border-t border-depth pt-4 text-[11px] leading-snug text-mist/70">
          Advisory only. Public or synthetic data. Effort proxy is an estimate,
          not catch or revenue. &copy; OpenStreetMap contributors for basemap tiles.
        </p>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mt-7">
      <h2 className="mb-2 text-sm font-bold uppercase tracking-wide text-surf">{title}</h2>
      {children}
    </section>
  );
}
