import type { Language } from '@/api/types';
import { LANGUAGES } from '@/lib/i18n';

interface LanguageSwitchProps {
  value: Language;
  onChange: (lang: Language) => void;
}

/**
 * English / Portuguese / Spanish switch for plan text (requirements.md Req 7).
 * Only words change — numbers and zone names stay identical (Req 7.2).
 */
export function LanguageSwitch({ value, onChange }: LanguageSwitchProps) {
  return (
    <div
      role="group"
      aria-label="Language"
      className="flex overflow-hidden rounded-lg border border-depth"
    >
      {LANGUAGES.map((l) => {
        const active = value === l.id;
        return (
          <button
            key={l.id}
            onClick={() => onChange(l.id)}
            aria-pressed={active}
            title={l.label}
            className={[
              'flex-1 px-2 py-1.5 text-[11px] font-bold tracking-wide transition-colors',
              active ? 'bg-tide text-foam' : 'bg-abyss/40 text-mist hover:text-foam',
            ].join(' ')}
          >
            {l.flag}
          </button>
        );
      })}
    </div>
  );
}
