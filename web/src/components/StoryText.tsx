import { checkWord, type WordStatus } from "../lib/decode";

// Word marks use shape as well as color: solid underline = can sound out, dotted = tricky word,
// boxed = uses a sound they don't know yet. Screen readers get the same words in text.
const MARK: Record<WordStatus, string> = {
  ok: "border-b-4 border-primary",
  tricky: "border-b-4 border-dotted border-idea",
  unknown: "rounded border-2 border-idea bg-notice-bg px-1 text-notice-text",
};
const SR: Record<WordStatus, string> = {
  ok: "",
  tricky: " (tricky word, teach first)",
  unknown: " (uses a sound they don't know yet)",
};

export function checkStory(words: string[], known: Set<string>) {
  const checked = words.map((w) => ({ w, status: checkWord(w, known) }));
  const tricky = [
    ...new Set(
      checked
        .filter((c) => c.status === "tricky")
        .map((c) => c.w.replace(/[^A-Za-z]/g, "").toLowerCase()),
    ),
  ];
  return { checked, tricky, unknown: checked.filter((c) => c.status === "unknown").length };
}

export function StoryText({
  words,
  known,
  className = "text-3xl leading-[2.6rem]",
}: {
  words: string[];
  known: Set<string>;
  className?: string;
}) {
  const { checked } = checkStory(words, known);
  return (
    <p className={`font-body ${className}`} data-testid="story">
      {checked.map(({ w, status }, i) => (
        <span key={i}>
          <span className={`inline-block pb-0.5 ${MARK[status]}`} data-status={status}>
            {w}
            <span className="sr-only">{SR[status]}</span>
          </span>{" "}
        </span>
      ))}
    </p>
  );
}

export function MarksLegend() {
  return (
    <ul
      className="flex flex-wrap gap-x-5 gap-y-1 text-sm text-muted"
      aria-label="What the marks mean"
    >
      <li className="flex items-center gap-2">
        <span aria-hidden="true" className="inline-block w-6 border-b-4 border-primary" /> can sound
        out
      </li>
      <li className="flex items-center gap-2">
        <span
          aria-hidden="true"
          className="inline-block w-6 border-b-4 border-dotted border-idea"
        />{" "}
        tricky word: teach first
      </li>
      <li className="flex items-center gap-2">
        <span
          aria-hidden="true"
          className="inline-block h-4 w-4 rounded border-2 border-idea bg-notice-bg"
        />{" "}
        uses a sound they don&apos;t know yet
      </li>
    </ul>
  );
}
