// Stroke icons, always used next to a text label (or given an aria-label). No emoji.
const PATHS: Record<string, string> = {
  book: "M6 3h12a1 1 0 0 1 1 1v16a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1Zm3 5h6M9 12h6",
  cap: "M2 9l10-5 10 5-10 5L2 9Zm4 3.5V17c0 1.5 3 3 6 3s6-1.5 6-3v-4.5",
  speaker: "M4 9v6h4l5 4V5L8 9H4Zm12 0a4 4 0 0 1 0 6m2.5-9a8 8 0 0 1 0 12",
  stop: "M7 7h10v10H7z",
  print: "M7 9V3h10v6M7 17H4v-7h16v7h-3M7 14h10v7H7z",
  board: "M3 4h18v12H3zM8 20h8M12 16v4",
  check: "M4 12l5 5L20 6",
  plus: "M12 5v14M5 12h14",
  left: "M15 5l-7 7 7 7",
  right: "M9 5l7 7-7 7",
  info: "M12 8h.01M11 12h1v5h1M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Z",
  alert: "M12 4 2 20h20L12 4Zm0 6v4m0 3h.01",
  close: "M6 6l12 12M18 6 6 18",
  sliders: "M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M20 18h0M14 4v4M8 10v4M16 16v4",
  search: "M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14Zm9 16-4-4",
  pencil: "M4 20l4-1L19 8l-3-3L5 16l-1 4Z",
  home: "M3 11l9-8 9 8M5 10v10h14V10",
};

export function Icon({
  name,
  className = "h-5 w-5",
}: {
  name: keyof typeof PATHS | string;
  className?: string;
}) {
  return (
    <svg
      viewBox="0 0 24 24"
      className={className}
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      <path d={PATHS[name] ?? ""} />
    </svg>
  );
}

export function Logo() {
  return (
    <svg viewBox="0 0 28 28" className="h-7 w-7" aria-hidden="true" focusable="false">
      <rect x="9" y="3" width="10" height="4" rx="2" fill="var(--color-highlight)" />
      <rect x="5" y="10" width="18" height="5" rx="2.5" fill="var(--color-ink)" />
      <rect x="3" y="18" width="22" height="5" rx="2.5" fill="var(--color-ink)" />
    </svg>
  );
}
