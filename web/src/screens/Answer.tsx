import { useMemo, useState } from "react";
import { ask, OFFER, sendFeedback, type AskResult } from "../api";
import { Link, navigate, PageTitle, useLocation } from "../app/router";
import { AskForm } from "../components/AskForm";
import { EvidenceLabel } from "../components/EvidenceLabel";
import { Icon } from "../components/Icon";
import { ReadAloud } from "../components/ReadAloud";
import { Citations, SourceList, SourcesScope } from "../components/Sources";
import { Badge, Breadcrumb, Button, Card, ErrorMessage, ExampleChip } from "../components/ui";
import { useGroups } from "../lib/groups";
import { useStored } from "../lib/storage";
import { useAsync } from "../lib/useAsync";

export function LoadingState() {
  return (
    <div
      role="status"
      className="rh-card rounded-2xl border border-border bg-surface p-8 text-center"
    >
      <p className="font-heading text-xl font-semibold">Looking through the approved research</p>
      <p className="mt-2 text-muted">
        We check every sentence against a source before we show it. This usually takes a few
        seconds.
      </p>
      <p aria-hidden="true" className="mt-5 flex justify-center gap-3">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="rh-pulse h-3 w-3 rounded-full bg-primary"
            style={{ animationDelay: `${i * 0.25}s` }}
          />
        ))}
      </p>
    </div>
  );
}

const NON_ANSWER: Record<string, { title: string; icon: string }> = {
  no_research: { title: "No research found", icon: "search" },
  insufficient: { title: "Not enough research to answer", icon: "search" },
  out_of_scope: { title: "That's outside what I can help with", icon: "info" },
  unavailable: { title: "Reading Helper is resting", icon: "info" },
};

const IDEAS = [
  "My kids know their letter sounds but can't read words",
  "How do I teach kids the difference between b and d?",
  "Should kids guess words from pictures?",
];

export function NoResearch({ a }: { a: AskResult }) {
  const meta = NON_ANSWER[a.kind] ?? NON_ANSWER.no_research;
  return (
    <Card aria-labelledby="no-research" className="max-w-3xl">
      <div className="flex flex-wrap items-center gap-3">
        <Badge tone="plain">{a.evidence_label}</Badge>
        {a.example && <ExampleChip />}
      </div>
      <h2
        id="no-research"
        className="mt-3 flex items-center gap-2 font-heading text-2xl font-semibold"
      >
        <Icon name={meta.icon} className="h-7 w-7 shrink-0" />
        {meta.title}
      </h2>
      <p className="mt-3 text-lg">{a.message}</p>
      <h3 className="mt-5 font-heading text-lg font-semibold">What I can help with</h3>
      <p className="mt-1">{a.offer || OFFER}</p>
      <h3 className="mt-5 font-heading text-lg font-semibold">Try one of these</h3>
      <ul className="mt-2 flex flex-col gap-2">
        {IDEAS.map((q) => (
          <li key={q}>
            <Link
              to="/ask"
              query={{ q }}
              className="inline-flex min-h-target items-center rounded-lg border border-control px-4 py-2 font-medium text-primary underline hover:bg-bg"
            >
              {q}
            </Link>
          </li>
        ))}
      </ul>
    </Card>
  );
}

function Feedback() {
  const [rating, setRating] = useState<string | null>(null);
  async function pick(r: "worked" | "so-so" | "stuck") {
    setRating(r);
    try {
      await sendFeedback({ rating: r });
    } catch {
      /* feedback is optional; never block the teacher */
    }
  }
  const opts = [
    ["worked", "It worked"],
    ["so-so", "So-so"],
    ["stuck", "Still stuck"],
  ] as const;
  return (
    <Card aria-labelledby="tried" className="no-print">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 id="tried" className="font-heading text-lg font-semibold">
          Tried it? How did it go?
        </h2>
        <div role="group" aria-labelledby="tried" className="flex flex-wrap gap-2">
          {opts.map(([k, label]) => (
            <Button
              key={k}
              aria-pressed={rating === k}
              onClick={() => pick(k)}
              variant={rating === k ? "primary" : "secondary"}
            >
              {label}
            </Button>
          ))}
        </div>
      </div>
      <p role="status" className="mt-2 text-sm text-muted">
        {rating
          ? "Thanks. This only helps us improve the answers; it is not about you or your students."
          : ""}
      </p>
    </Card>
  );
}

function AddToGroup({ title, steps }: { title: string; steps: string[] }) {
  const [groups] = useGroups();
  const [added, setAdded] = useStored<Record<string, { title: string; steps: string[] }[]>>(
    "rh-added",
    {},
  );
  const [open, setOpen] = useState(false);
  const [gid, setGid] = useState(groups[0]?.id ?? "");
  const [done, setDone] = useState<string | null>(null);
  if (!open)
    return (
      <>
        <Button onClick={() => setOpen(true)} aria-expanded={false}>
          Add to a group&apos;s plan
        </Button>
        <span role="status" className="font-semibold">
          {done ? `Added to ${done}\u2019s plan.` : ""}
        </span>
      </>
    );
  return (
    <div className="flex flex-wrap items-end gap-2" role="group" aria-label="Add to a group's plan">
      <div>
        <label htmlFor="which-group" className="block text-sm font-semibold">
          Which group?
        </label>
        <select
          id="which-group"
          value={gid}
          onChange={(e) => setGid(e.target.value)}
          className="min-h-target rounded-lg border border-control bg-surface px-3"
        >
          {groups.map((g) => (
            <option key={g.id} value={g.id}>
              {g.label}
            </option>
          ))}
        </select>
      </div>
      <Button
        variant="primary"
        disabled={!gid}
        onClick={() => {
          setAdded({ ...added, [gid]: [...(added[gid] ?? []), { title, steps }] });
          setDone(groups.find((g) => g.id === gid)?.label ?? "the group");
          setOpen(false);
        }}
      >
        Add
      </Button>
      <Button variant="quiet" onClick={() => setOpen(false)}>
        Cancel
      </Button>
    </div>
  );
}

function AnswerBody({ a }: { a: AskResult }) {
  const totalMin = a.idea_for_class.reduce((n, s) => n + s.minutes, 0);
  const speech = useMemo(
    () =>
      [
        `How sure: ${a.evidence_label}.`,
        a.short_answer,
        ...a.research_says.map((c) => c.text),
        a.idea_for_class.length ? "Idea for your class." : "",
        ...a.idea_for_class.map((s, i) => `Step ${i + 1}. ${s.text}`),
      ]
        .filter(Boolean)
        .join(" "),
    [a],
  );
  return (
    <SourcesScope sources={a.sources} example={!!a.example}>
      <div className="mt-4 flex flex-wrap items-center gap-3">
        <ReadAloud text={speech} />
        {a.example && <ExampleChip />}
      </div>
      <div className="mt-4 grid gap-5 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <div className="flex flex-col gap-5">
          <Card aria-labelledby="research-says" className="border-2 border-primary">
            <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
              <h2 id="research-says" className="m-0">
                <Badge>Research says</Badge>
              </h2>
              <EvidenceLabel label={a.evidence_label} mixed={a.mixed} />
            </div>
            <p className="mt-3 text-lg">{a.short_answer}</p>
            {a.research_says.length > 0 && (
              <ul className="mt-3 flex flex-col gap-2">
                {a.research_says.map((c) => (
                  <li key={c.text} className="flex flex-wrap items-center gap-x-2">
                    <span>{c.text}</span>
                    <Citations ns={c.citations} />
                  </li>
                ))}
              </ul>
            )}
            {a.watch_out && (
              <div className="mt-4 rounded-lg bg-notice-bg p-3 text-notice-text">
                <h3 className="flex items-center gap-2 font-heading font-semibold">
                  <Icon name="alert" /> Watch out for
                </h3>
                <p className="mt-1">
                  <strong>Myth:</strong> {a.watch_out.myth} <strong>Instead:</strong>{" "}
                  {a.watch_out.correction} <Citations ns={a.watch_out.citations} />
                </p>
              </div>
            )}
          </Card>

          {a.idea_for_class.length > 0 && (
            <Card aria-labelledby="idea" className="border-2 border-idea">
              <div className="flex flex-wrap items-center gap-3">
                <h2 id="idea" className="m-0">
                  <Badge tone="idea">Idea for your class</Badge>
                </h2>
                <span className="font-heading text-lg font-semibold">{totalMin} minutes</span>
              </div>
              <p className="mt-2 text-sm text-muted">
                Our suggestion, based on the research above. It is not itself a research finding.
              </p>
              <ol className="mt-3 flex list-decimal flex-col gap-2 pl-6">
                {a.idea_for_class.map((s) => (
                  <li key={s.text}>
                    {s.text}{" "}
                    <span className="whitespace-nowrap text-sm text-muted">({s.minutes} min)</span>
                  </li>
                ))}
              </ol>
              <div className="no-print mt-4 flex flex-wrap items-end gap-2">
                <Button
                  variant="primary"
                  icon="board"
                  onClick={() =>
                    navigate("/board", {
                      mode: "steps",
                      title: "Idea for your class",
                      s: a.idea_for_class.map((s) => s.text).join("|"),
                    })
                  }
                >
                  Show on the class board
                </Button>
                <AddToGroup
                  title="Idea from your question"
                  steps={a.idea_for_class.map((s) => s.text)}
                />
                <Button icon="print" onClick={() => window.print()}>
                  Print this idea
                </Button>
              </div>
            </Card>
          )}
          <Feedback />
        </div>

        <div className="flex flex-col gap-5">
          <SourceList />
          <aside className="rounded-2xl border border-dashed border-control p-4 text-sm text-muted">
            <h2 className="font-heading font-semibold text-ink">How we made this answer</h2>
            <p className="mt-1">Searched the approved sources · {a.sources.length} matched</p>
            <p>Every sentence is checked against a source.</p>
          </aside>
        </div>
      </div>
    </SourcesScope>
  );
}

export default function Answer() {
  const { query } = useLocation();
  const q = query.get("q") ?? "";
  const { data, error, loading, retry } = useAsync(
    () => (q ? ask({ question: q }) : Promise.reject(new Error("empty"))),
    q,
  );

  return (
    <>
      <Breadcrumb items={[{ label: "Home", to: "/" }, { label: "Your answer" }]} />
      <p className="text-sm text-muted">You asked</p>
      <PageTitle title="Your answer">{q ? `“${q}”` : "Ask a question"}</PageTitle>

      {!q && (
        <div className="mt-4 max-w-3xl">
          <AskForm id="ask-here" label="Your question:" />
        </div>
      )}
      <div aria-live="polite" className="mt-4">
        {q && loading && <LoadingState />}
        {q && error && <ErrorMessage onRetry={retry}>{error}</ErrorMessage>}
        {data && data.kind !== "answer" && <NoResearch a={data} />}
        {data && data.kind === "answer" && <AnswerBody a={data} />}
      </div>
      {data && (
        <div className="mt-8 max-w-3xl no-print">
          <AskForm id="ask-another" label="Ask another question:" />
        </div>
      )}
    </>
  );
}
