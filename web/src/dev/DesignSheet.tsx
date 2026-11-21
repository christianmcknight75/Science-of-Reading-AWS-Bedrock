// Dev-only sheet (route #/design, only when running `npm run dev`): the three mascot options and
// the four states of the chosen one. Used for docs/mascot-options.png and docs/mascot-states.png.
import { Mascot } from "../components/Mascot";

const NAVY = "var(--color-primary)";
const GOLD = "var(--color-highlight)";
const CREAM = "var(--color-warm)";

function Ribbon() {
  // Option B: a bookmark creature
  return (
    <svg viewBox="0 0 130 120" width="130" height="120" aria-hidden="true" focusable="false">
      <path d="M38 14 H92 V104 L65 88 L38 104 Z" fill={NAVY} />
      <path d="M38 14 H92 V26 H38 Z" fill={GOLD} />
      <circle cx="55" cy="52" r="7" fill="#fff" />
      <circle cx="75" cy="52" r="7" fill="#fff" />
      <circle cx="55" cy="53" r="3.3" fill="var(--color-ink)" />
      <circle cx="75" cy="53" r="3.3" fill="var(--color-ink)" />
      <path
        d="M56 68 Q65 76 74 68"
        stroke={CREAM}
        strokeWidth="3"
        strokeLinecap="round"
        fill="none"
      />
    </svg>
  );
}
function Stack() {
  // Option C: the logo's stacked bars with eyes
  return (
    <svg viewBox="0 0 130 120" width="130" height="120" aria-hidden="true" focusable="false">
      <rect x="40" y="18" width="50" height="16" rx="8" fill={GOLD} />
      <rect x="22" y="40" width="86" height="26" rx="13" fill="var(--color-ink)" />
      <rect x="14" y="72" width="102" height="30" rx="15" fill="var(--color-ink)" />
      <circle cx="52" cy="53" r="6" fill="#fff" />
      <circle cx="78" cy="53" r="6" fill="#fff" />
      <circle cx="53" cy="54" r="3" fill="var(--color-ink)" />
      <circle cx="79" cy="54" r="3" fill="var(--color-ink)" />
    </svg>
  );
}

export default function DesignSheet() {
  const box = "flex flex-col items-center gap-2 rounded-2xl border border-border bg-surface p-5";
  return (
    <div className="flex flex-col gap-8">
      <h1 className="font-heading text-3xl">Mascot options and states (dev only)</h1>
      <section aria-label="Options" data-testid="options" className="flex flex-wrap gap-5">
        <figure className={box}>
          <Mascot size={150} />
          <figcaption className="font-semibold">A. Wren (chosen)</figcaption>
        </figure>
        <figure className={box}>
          <Ribbon />
          <figcaption className="font-semibold">B. Ribbon</figcaption>
        </figure>
        <figure className={box}>
          <Stack />
          <figcaption className="font-semibold">C. Stack</figcaption>
        </figure>
      </section>
      <section aria-label="States" data-testid="states" className="flex flex-wrap gap-5">
        {(["idle", "thinking", "pointing", "nothing"] as const).map((s) => (
          <figure key={s} className={box}>
            <Mascot state={s} size={150} />
            <figcaption className="font-semibold">
              {s === "nothing" ? "nothing found" : s}
            </figcaption>
          </figure>
        ))}
      </section>
    </div>
  );
}
