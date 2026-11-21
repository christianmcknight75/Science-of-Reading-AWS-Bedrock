import { useState } from "react";
import { diagnoseMistakes, type MistakePair, type MistakeResult } from "../api";
import { ApiError } from "../api";
import { PageTitle } from "../app/router";
import { AddToGroup } from "../components/AddToGroup";
import { EvidenceLabel } from "../components/EvidenceLabel";
import { Citations, SourceList, SourcesScope } from "../components/Sources";
import { TeachingNav } from "../components/TeachingNav";
import { Badge, Button, Card, ErrorMessage, ExampleChip } from "../components/ui";

const COMMON: MistakePair[] = [
  { word: "ship", said: "sip" },
  { word: "stop", said: "top" },
  { word: "bit", said: "bat" },
  { word: "pony", said: "horse" },
];

export default function Stuck() {
  const [rows, setRows] = useState<MistakePair[]>([{ word: "", said: "" }]);
  const [result, setResult] = useState<MistakeResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const set = (i: number, k: keyof MistakePair, v: string) =>
    setRows(rows.map((r, j) => (j === i ? { ...r, [k]: v } : r)));
  const filled = rows.filter((r) => r.word.trim() && r.said.trim());

  async function find() {
    setBusy(true);
    setError(null);
    try {
      setResult(await diagnoseMistakes(filled));
    } catch (e) {
      setResult(null);
      setError(e instanceof ApiError ? e.message : "Something went wrong. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <TeachingNav current="/teaching/stuck" />
      <PageTitle>Why is a kid stuck?</PageTitle>
      <p className="mt-2 text-lg text-muted">
        Tell us the word and what the child said. We find the skill behind the mistake and what to
        do next.
      </p>

      <div className="mt-5 grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <Card aria-labelledby="mistakes">
          <h2 id="mistakes" className="font-heading text-xl font-semibold">
            What happened
          </h2>
          <div className="mt-3" role="group" aria-label="Try a common mistake">
            <p className="font-semibold">Try a common mistake</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {COMMON.map((c) => (
                <Button key={c.word} onClick={() => setRows([c])}>
                  {c.word} → {c.said}
                </Button>
              ))}
            </div>
          </div>
          <form
            className="mt-4 flex flex-col gap-4"
            onSubmit={(e) => {
              e.preventDefault();
              if (filled.length) void find();
            }}
          >
            {rows.map((r, i) => (
              <fieldset key={i} className="grid gap-3 sm:grid-cols-2">
                <legend className="mb-1 font-semibold">Mistake {i + 1}</legend>
                <div>
                  <label htmlFor={`w${i}`} className="block">
                    The word
                  </label>
                  <input
                    id={`w${i}`}
                    value={r.word}
                    onChange={(e) => set(i, "word", e.target.value)}
                    maxLength={30}
                    autoComplete="off"
                    className="min-h-target w-full rounded-lg border border-control bg-surface px-3"
                  />
                </div>
                <div>
                  <label htmlFor={`s${i}`} className="block">
                    What they said
                  </label>
                  <input
                    id={`s${i}`}
                    value={r.said}
                    onChange={(e) => set(i, "said", e.target.value)}
                    maxLength={30}
                    autoComplete="off"
                    className="min-h-target w-full rounded-lg border border-control bg-surface px-3"
                  />
                </div>
              </fieldset>
            ))}
            <div className="flex flex-wrap gap-2">
              <Button type="submit" variant="primary" disabled={!filled.length || busy}>
                {busy ? "Looking…" : "Find the skill"}
              </Button>
              <Button icon="plus" onClick={() => setRows([...rows, { word: "", said: "" }])}>
                Add another mistake
              </Button>
            </div>
          </form>
          <p className="mt-3 text-sm text-muted">
            No names needed. We don&apos;t save this unless you add it to a group plan.
          </p>
        </Card>

        <div aria-live="polite" className="flex flex-col gap-5">
          {error && <ErrorMessage onRetry={() => void find()}>{error}</ErrorMessage>}
          {result?.kind === "no_match" && (
            <Card aria-labelledby="nomatch">
              <Badge tone="plain">No research found</Badge>
              <h2 id="nomatch" className="mt-2 font-heading text-xl font-semibold">
                We can&apos;t tell yet
              </h2>
              <p className="mt-2">{result.message}</p>
            </Card>
          )}
          {result?.kind === "match" && (
            <SourcesScope sources={result.sources} example={!!result.example}>
              <Card aria-labelledby="going-on" className="border-2 border-primary">
                <div className="flex flex-wrap items-center gap-3">
                  <h2 id="going-on" className="m-0">
                    <Badge>Research says</Badge>
                  </h2>
                  <EvidenceLabel label={result.evidence_label} />
                  {result.example && <ExampleChip />}
                </div>
                <p className="mt-3 text-sm font-bold uppercase tracking-wide text-muted">
                  What&apos;s going on
                </p>
                <p className="text-xl font-semibold">
                  {result.pattern} <Citations ns={result.sources.map((s) => s.n)} />
                </p>
                <p className="mt-2">
                  <strong>Skill to work on:</strong> {result.skill}
                </p>
                <p className="mt-2 text-sm text-muted">
                  How sure about the pattern: {result.evidence_note}
                </p>
              </Card>
              {result.try_it && (
                <Card aria-labelledby="try" className="border-2 border-idea">
                  <h2 id="try" className="m-0 flex flex-wrap items-center gap-3">
                    <Badge tone="idea">Idea for your class</Badge>
                    <span className="font-heading text-lg">
                      Try this · {result.try_it.minutes} min
                    </span>
                  </h2>
                  <p className="mt-2">{result.try_it.text}</p>
                  <p className="mt-2 text-muted">{result.also_watch}</p>
                  <div className="mt-3 flex flex-wrap items-end gap-2">
                    <AddToGroup title={`Try this: ${result.skill}`} steps={[result.try_it.text]} />
                  </div>
                </Card>
              )}
              <SourceList />
            </SourcesScope>
          )}
        </div>
      </div>
    </>
  );
}
