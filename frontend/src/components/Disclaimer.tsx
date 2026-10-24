/**
 * Advisory disclaimer, always visible (requirements.md Req 9.1). Fathom never
 * claims legal compliance — it only reports which known zones a plan avoids.
 */
export function Disclaimer() {
  return (
    <p className="pointer-events-none text-center text-[10px] leading-snug text-mist/80">
      Advisory only. Does not replace official notices, VHF warnings, or the
      captain&apos;s judgment.
    </p>
  );
}
