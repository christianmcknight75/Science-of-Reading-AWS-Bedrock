const LEVEL: Record<string, { bars: number; expert: string }> = {
  "Very sure": { bars: 3, expert: "strong evidence" },
  "Fairly sure": { bars: 2, expert: "moderate evidence" },
  "Not sure yet": { bars: 1, expert: "limited evidence" },
  "No research found": { bars: 0, expert: "no evidence found" },
};

/** The evidence label always comes first. Plain words, the expert word small, never color alone. */
export function EvidenceLabel({ label, mixed = false }: { label: string; mixed?: boolean }) {
  const lv = LEVEL[label] ?? LEVEL["Not sure yet"];
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1" data-testid="evidence-label">
      <span>
        How sure: <strong>{label}</strong>
      </span>
      <span aria-hidden="true" className="flex gap-1">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className={`h-2 w-5 rounded-sm border border-primary ${i < lv.bars ? "bg-primary" : "bg-surface"}`}
          />
        ))}
      </span>
      <span className="text-sm text-muted">
        ({lv.expert}
        {mixed ? "; the research is mixed" : ""})
      </span>
      <span className="sr-only">
        {lv.bars} of 3 bars filled.
        {mixed ? " The research is mixed." : ""}
      </span>
    </div>
  );
}
