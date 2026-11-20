import * as Dialog from "@radix-ui/react-dialog";
import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import type { SourceOut } from "../api";
import { Button } from "./ui";

const TYPE_LABEL: Record<string, string> = {
  practice_guide: "practice guide",
  meta_analysis: "meta-analysis",
  study: "single study",
  foundational: "foundational report",
};
export const typeLabel = (t: string) => TYPE_LABEL[t] ?? t.replace("_", " ");

interface Ctx {
  sources: SourceOut[];
  example: boolean;
  open: (n: number) => void;
}
const SourcesContext = createContext<Ctx | null>(null);

/** Wrap an answer in this. Citation buttons and the source list open the same panel. */
export function SourcesScope({
  sources,
  example,
  children,
}: {
  sources: SourceOut[];
  example: boolean;
  children: ReactNode;
}) {
  const [active, setActive] = useState<number | null>(null);
  const returnTo = useRef<HTMLElement | null>(null);
  const ctx = useMemo<Ctx>(
    () => ({
      sources,
      example,
      open: (n) => {
        returnTo.current = document.activeElement as HTMLElement | null;
        setActive(n);
      },
    }),
    [sources, example],
  );
  return (
    <SourcesContext.Provider value={ctx}>
      {children}
      <Dialog.Root
        open={active !== null}
        onOpenChange={(o) => {
          if (!o) setActive(null);
        }}
      >
        <Dialog.Portal>
          <Dialog.Overlay className="rh-overlay no-print fixed inset-0 z-40 bg-black/50" />
          <Dialog.Content
            onCloseAutoFocus={(e) => {
              e.preventDefault(); // we opened from buttons, not a Dialog.Trigger
              returnTo.current?.focus();
            }}
            className="rh-panel no-print fixed inset-y-0 right-0 z-50 flex w-full max-w-xl flex-col overflow-y-auto border-l border-border bg-surface p-5 shadow-float"
          >
            <div className="mb-3 flex items-start justify-between gap-3">
              <Dialog.Title className="font-heading text-2xl font-semibold">Sources</Dialog.Title>
              <Dialog.Close asChild>
                <Button icon="close" aria-label="Close sources">
                  Close
                </Button>
              </Dialog.Close>
            </div>
            <Dialog.Description className="mb-4 text-muted">
              The exact passage each statement comes from, and the printed page.
            </Dialog.Description>
            {example && <ExampleNote />}
            <ol className="flex flex-col gap-4">
              {sources.map((s) => (
                <li key={s.n}>
                  <SourceCard source={s} active={s.n === active} />
                </li>
              ))}
            </ol>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </SourcesContext.Provider>
  );
}

const ExampleNote = () => (
  <p className="mb-4 rounded-lg bg-notice-bg p-3 text-sm text-notice-text">
    <strong>Example.</strong> These passages are sample text for trying the screens. They are not
    real quotations. In the live app this shows the exact words from the source.
  </p>
);

function Quoted({ text, quote }: { text: string; quote: string | null }) {
  const i = quote ? text.indexOf(quote) : -1;
  if (!quote || i < 0) return <>{text}</>;
  return (
    <>
      {text.slice(0, i)}
      <mark className="rh-quote">
        <span className="sr-only">Exact words used start: </span>
        {quote}
        <span className="sr-only"> Exact words used end.</span>
      </mark>
      {text.slice(i + quote.length)}
    </>
  );
}

function SourceCard({ source: s, active }: { source: SourceOut; active: boolean }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (active) ref.current?.scrollIntoView({ block: "nearest" });
  }, [active]);
  return (
    <div
      ref={ref}
      className={`rounded-xl border p-4 ${active ? "border-2 border-primary" : "border-border"}`}
    >
      <h3 className="font-heading text-base font-semibold">
        <span className="mr-2 inline-flex h-7 min-w-7 items-center justify-center rounded-full bg-primary px-2 text-sm text-white">
          <span className="sr-only">Source </span>
          {s.n}
        </span>
        {s.title}
      </h3>
      <p className="mt-1 text-sm text-muted">
        {s.year ?? "n.d."} · {typeLabel(s.source_type)}
        {s.section ? ` · ${s.section}` : ""}
        {s.page ? ` · page ${s.page}` : ""}
      </p>
      <blockquote className="mt-3 border-l-4 border-control pl-3">
        <Quoted text={s.passage_text} quote={s.quote} />
      </blockquote>
    </div>
  );
}

/** Numbered citation: opens the panel on that source. 48px so it is easy to tap. */
export function Citation({ n }: { n: number }) {
  const c = useContext(SourcesContext);
  const s = c?.sources.find((x) => x.n === n);
  if (!c || !s) return null;
  return (
    <button
      type="button"
      onClick={() => c.open(n)}
      aria-label={`Source ${n}: ${s.title}. Opens the exact passage.`}
      aria-haspopup="dialog"
      className="inline-flex min-h-target min-w-target items-center justify-center rounded-full border-2 border-primary bg-surface px-2 font-bold text-primary hover:bg-bg"
    >
      {n}
    </button>
  );
}

export function Citations({ ns }: { ns: number[] }) {
  if (!ns.length) return null;
  return (
    <span className="inline-flex flex-wrap items-center gap-1 align-middle">
      <span className="sr-only">Sources:</span>
      {ns.map((n) => (
        <Citation key={n} n={n} />
      ))}
    </span>
  );
}

/** "Where this comes from": the always-visible list beside (or under) the answer. */
export function SourceList() {
  const c = useContext(SourcesContext);
  if (!c || c.sources.length === 0) return null;
  return (
    <aside
      aria-labelledby="where-from"
      className="rh-card rounded-2xl border border-border bg-surface p-5"
    >
      <h2 id="where-from" className="font-heading text-lg font-semibold">
        Where this comes from
      </h2>
      <ol className="mt-3 flex flex-col gap-4">
        {c.sources.map((s) => (
          <li key={s.n} className="border-t border-border pt-3 first:border-0 first:pt-0">
            <p className="font-semibold">
              <span className="mr-1">{s.n}.</span>
              {s.title}
            </p>
            <p className="text-sm text-muted">
              {s.year ?? "n.d."} · {typeLabel(s.source_type)}
              {s.page ? ` · page ${s.page}` : ""}
            </p>
            <Button
              onClick={() => c.open(s.n)}
              icon="search"
              className="mt-2"
              aria-haspopup="dialog"
              aria-label={`Show exact passage from source ${s.n}`}
            >
              Show exact passage
            </Button>
          </li>
        ))}
      </ol>
    </aside>
  );
}
