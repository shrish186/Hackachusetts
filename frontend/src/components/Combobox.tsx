import { useEffect, useId, useMemo, useRef, useState } from 'react';

export interface ComboOption {
  id: string;
  /** Primary label used for display and matching. */
  label: string;
  /** Extra text matched against (e.g. id, aliases). */
  keywords?: string;
  /** Small muted subtitle (e.g. lat/lon). */
  subtitle?: string;
  /** Short badge shown after the label (e.g. "MA"). */
  badge?: string;
  /** Optional right-aligned chip node (e.g. a red "Closed …" chip). */
  chip?: React.ReactNode;
}

interface ComboboxProps {
  label: string;
  options: ComboOption[];
  /** Currently selected option id, or '' when none. */
  value: string;
  onChange: (id: string) => void;
  placeholder?: string;
  /** Validation message shown when the typed text matches no option. */
  invalidMessage?: string;
  /** Called with the DOM-order option id when the active option changes. */
  disabled?: boolean;
}

/** Normalize for case/accent-insensitive matching (item 1). */
function fold(s: string): string {
  return s
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase();
}

/**
 * Accessible single-select combobox (items 1 & 2).
 *
 * - role=combobox on the input, role=listbox on the popup, role=option per row
 * - aria-activedescendant tracks the highlighted option
 * - ArrowUp/Down move the highlight, Enter selects, Escape closes
 * - opens on focus; filters as the user types (case/accent-insensitive, matches
 *   label + keywords)
 * - only a valid option can be committed; free text that matches nothing shows
 *   `invalidMessage` and clears the value
 */
export function Combobox({
  label,
  options,
  value,
  onChange,
  placeholder,
  invalidMessage = 'Pick an option from the list',
  disabled,
}: ComboboxProps) {
  const listId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLUListElement>(null);

  const selected = options.find((o) => o.id === value) ?? null;
  const [query, setQuery] = useState(selected ? selected.label : '');
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const [touched, setTouched] = useState(false);
  // True only while the user is actively typing a filter (vs. the box showing
  // the committed selection's label). When false we show the full list.
  const [typing, setTyping] = useState(false);

  // Keep the input text in sync when the value changes from outside.
  useEffect(() => {
    const sel = options.find((o) => o.id === value) ?? null;
    setQuery(sel ? sel.label : '');
    setTyping(false);
  }, [value, options]);

  const filtered = useMemo(() => {
    // Only filter once the user has typed; otherwise show every option so a
    // committed selection's label never hides the rest of the list.
    const q = typing ? fold(query.trim()) : '';
    if (!q) return options;
    return options.filter(
      (o) => fold(o.label).includes(q) || fold(o.keywords ?? '').includes(q) || fold(o.id).includes(q),
    );
  }, [query, options, typing]);

  // Clamp the active index whenever the filtered list changes.
  useEffect(() => {
    setActive((a) => Math.max(0, Math.min(a, filtered.length - 1)));
  }, [filtered.length]);

  function commit(opt: ComboOption | undefined) {
    if (!opt) return;
    onChange(opt.id);
    setQuery(opt.label);
    setOpen(false);
    setTyping(false);
    setTouched(true);
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (!open) setOpen(true);
      setActive((a) => Math.min(a + 1, filtered.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (!open) setOpen(true);
      setActive((a) => Math.max(a - 1, 0));
    } else if (e.key === 'Enter') {
      if (open && filtered[active]) {
        e.preventDefault();
        commit(filtered[active]);
      }
    } else if (e.key === 'Escape') {
      setOpen(false);
      // Restore the committed selection text.
      setQuery(selected ? selected.label : '');
      inputRef.current?.blur();
    }
  }

  // Scroll the active option into view.
  useEffect(() => {
    if (!open || !listRef.current) return;
    const el = listRef.current.querySelector<HTMLElement>(`[data-idx="${active}"]`);
    el?.scrollIntoView({ block: 'nearest' });
  }, [active, open]);

  const activeId = open && filtered[active] ? `${listId}-opt-${active}` : undefined;
  const showInvalid = touched && !open && query.trim() !== '' && !selected;

  return (
    <div className="relative">
      <input
        ref={inputRef}
        type="text"
        role="combobox"
        aria-expanded={open}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={activeId}
        aria-label={label}
        aria-invalid={showInvalid || undefined}
        autoComplete="off"
        disabled={disabled}
        value={query}
        placeholder={placeholder}
        onFocus={(e) => {
          setOpen(true);
          // Select the text so the first keystroke replaces the label and the
          // full list stays visible until the user actually types.
          e.target.select();
        }}
        onBlur={() => {
          // Delay so option mousedown can fire first.
          window.setTimeout(() => {
            setOpen(false);
            setTouched(true);
            setTyping(false);
            // If there's a committed selection, restore its label. If not (and
            // the user typed something that matched nothing), keep the text so
            // the "Pick a …" invalid message shows.
            if (selected) setQuery(selected.label);
          }, 120);
        }}
        onChange={(e) => {
          setQuery(e.target.value);
          setTyping(true);
          setOpen(true);
          setActive(0);
        }}
        onKeyDown={onKeyDown}
        className="mt-1 w-full rounded-lg border border-depth bg-abyss/60 px-3 py-2 text-sm text-foam outline-none focus:border-surf focus-visible:ring-2 focus-visible:ring-surf"
      />

      {open && filtered.length > 0 && (
        <ul
          ref={listRef}
          id={listId}
          role="listbox"
          aria-label={label}
          className="absolute z-40 mt-1 max-h-60 w-full overflow-y-auto overscroll-contain rounded-lg border border-depth bg-deep shadow-2xl"
        >
          {filtered.map((o, i) => {
            const isActive = i === active;
            const isSel = o.id === value;
            return (
              <li
                key={o.id}
                id={`${listId}-opt-${i}`}
                data-idx={i}
                role="option"
                aria-selected={isSel}
                onMouseDown={(e) => {
                  e.preventDefault();
                  commit(o);
                }}
                onMouseEnter={() => setActive(i)}
                className={[
                  'flex cursor-pointer items-center justify-between gap-2 px-3 py-2 text-sm',
                  isActive ? 'bg-tide/30 text-foam' : 'text-mist',
                ].join(' ')}
              >
                <span className="min-w-0">
                  <span className="font-semibold text-foam">{o.label}</span>
                  {o.badge && (
                    <span className="ml-1.5 rounded bg-current/30 px-1 text-[10px] font-bold text-mist">
                      {o.badge}
                    </span>
                  )}
                  {o.subtitle && (
                    <span className="block truncate text-[11px] text-mist/80">{o.subtitle}</span>
                  )}
                </span>
                {o.chip && <span className="shrink-0">{o.chip}</span>}
              </li>
            );
          })}
        </ul>
      )}

      {showInvalid && (
        <p className="mt-1 text-[11px] text-alert" role="alert">
          {invalidMessage}
        </p>
      )}
    </div>
  );
}
