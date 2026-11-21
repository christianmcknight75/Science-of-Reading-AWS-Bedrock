import { useState } from "react";
import { getTrainingPlan } from "../api";
import { navigate, PageTitle } from "../app/router";
import { EvidenceLabel } from "../components/EvidenceLabel";
import { RadioChips } from "../components/RadioChips";
import { Citations, SourceList, SourcesScope } from "../components/Sources";
import { TrainingNav } from "../components/TrainingNav";
import { Badge, Breadcrumb, Button, Card, ErrorMessage, ExampleChip } from "../components/ui";
import { useSettings } from "../app/settings";
import { useStored } from "../lib/storage";
import { useAsync } from "../lib/useAsync";

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"] as const;
const WHO = ["Whole class", "Small group", "One student"] as const;
const LOOK = ["Most of them", "About half", "Only a few"] as const;

export default function TrainingTopic({ id }: { id: string }) {
  const { settings } = useSettings();
  const { data, error, loading, retry } = useAsync(() => getTrainingPlan(id), id);
  const [day, setDay] = useState<(typeof DAYS)[number]>("Thu");
  const [who, setWho] = useState<(typeof WHO)[number]>("Small group");
  const [short, setShort] = useState(false);
  const [look, setLook] = useState<(typeof LOOK)[number] | null>(null);
  const [week, setWeek] = useStored<Record<string, string[]>>("rh-week", {});
  const [done, setDone] = useState("");

  const stepsLabel = ["Remember it", "Plan it", "Try it", "Look back"];
  return (
    <>
      <TrainingNav current="/training" />
      <Breadcrumb
        items={[{ label: "My training", to: "/training" }, { label: data?.topic.title ?? "Topic" }]}
      />
      {loading && (
        <p
          role="status"
          className="rh-pulse rounded-2xl border border-border bg-surface p-6 text-lg"
        >
          Turning this topic into a plan…
        </p>
      )}
      {error && (
        <>
          <PageTitle title="Training topic">We couldn&apos;t load this topic</PageTitle>
          <div className="mt-4">
            <ErrorMessage onRetry={retry}>{error}</ErrorMessage>
          </div>
        </>
      )}
      {data && (
        <SourcesScope sources={data.sources} example={!!data.example}>
          <p className="text-sm font-bold uppercase tracking-wide text-muted">
            From training to tomorrow
          </p>
          <PageTitle title={data.topic.title}>{data.topic.title}</PageTitle>
          {settings.trainingWords && (
            <p className="mt-1 text-muted">
              In your training this may have been called {data.topic.training_word}.
            </p>
          )}
          <ol aria-label="Steps" className="mt-4 flex flex-wrap gap-2">
            {stepsLabel.map((s, i) => (
              <li key={s} className="rounded-lg border border-control bg-surface px-4 py-2">
                <span className="text-sm text-muted">Step {i + 1}</span>
                <br />
                <span className="font-semibold">{s}</span>
              </li>
            ))}
          </ol>

          <div className="mt-5 grid gap-5 lg:grid-cols-[minmax(0,1fr)_20rem]">
            <div className="flex flex-col gap-5">
              <Card aria-labelledby="s1" className="border-2 border-primary">
                <h2 id="s1" className="font-heading text-xl font-semibold">
                  1. Remember it{" "}
                  <span className="text-base font-normal text-muted">About 1 minute</span>
                </h2>
                <p className="mt-2 text-lg">{data.remember.sentence}</p>
                <ul className="mt-3 flex flex-wrap gap-3" aria-label="Sounds to hear">
                  {data.remember.sounds.map((s) => (
                    <li
                      key={s.letter}
                      className="flex min-h-target items-center gap-2 rounded-lg border-2 border-ink px-3 py-1"
                    >
                      <span className="text-2xl font-bold">{s.letter}</span>
                      {settings.soundHints && <span>{s.hint}</span>}
                    </li>
                  ))}
                </ul>
                <p className="mt-3 rounded-lg bg-bg p-3">{data.remember.tip}</p>
                <div className="mt-4 flex flex-wrap items-center gap-3">
                  <h3 className="m-0">
                    <Badge>Research says</Badge>
                  </h3>
                  <EvidenceLabel label={data.evidence_label} />
                  {data.example && <ExampleChip />}
                </div>
                <ul className="mt-2 flex flex-col gap-2">
                  {data.research_says.map((c) => (
                    <li key={c.text} className="flex flex-wrap items-center gap-x-2">
                      <span>{c.text}</span>
                      <Citations ns={c.citations} />
                    </li>
                  ))}
                </ul>
              </Card>

              <Card aria-labelledby="s2">
                <h2 id="s2" className="font-heading text-xl font-semibold">
                  2. Plan it
                </h2>
                <div className="mt-3 flex flex-col gap-4">
                  <RadioChips
                    legend="Which day?"
                    name="day"
                    value={day}
                    onChange={setDay}
                    options={DAYS.map((d) => ({ value: d, label: d }))}
                  />
                  <RadioChips
                    legend="With who?"
                    name="who"
                    value={who}
                    onChange={setWho}
                    options={WHO.map((d) => ({ value: d, label: d }))}
                  />
                </div>
                {(() => {
                  const idea = short ? data.short_idea : data.idea;
                  return (
                    <div className="mt-4 rounded-xl border-2 border-idea p-4">
                      <div className="flex flex-wrap items-center gap-3">
                        <h3 className="m-0">
                          <Badge tone="idea">Idea for your class</Badge>
                        </h3>
                        <span className="text-sm text-muted">
                          Our suggestion, based on the research above
                        </span>
                      </div>
                      <p className="mt-2 font-heading text-lg font-semibold">
                        {idea.title} · {idea.minutes} minutes
                      </p>
                      <ol className="mt-2 flex list-decimal flex-col gap-2 pl-6">
                        {idea.steps.map((s) => (
                          <li key={s}>{s}</li>
                        ))}
                      </ol>
                      <p className="mt-3">
                        <strong>You need:</strong> {idea.need}
                      </p>
                      <div className="no-print mt-4 flex flex-wrap items-center gap-2">
                        <Button
                          variant="primary"
                          onClick={() => {
                            setWeek({ ...week, [day]: [...(week[day] ?? []), data.topic.title] });
                            setDone(`Added to ${day}.`);
                          }}
                        >
                          Add to {day}
                        </Button>
                        <Button icon="print" onClick={() => window.print()}>
                          Print card and sound boxes
                        </Button>
                        <Button onClick={() => setShort(!short)} aria-pressed={short}>
                          {short ? "Show the full idea" : "Make it shorter"}
                        </Button>
                        <span role="status" className="font-semibold">
                          {done}
                        </span>
                      </div>
                    </div>
                  );
                })()}
              </Card>

              <Card aria-labelledby="s3">
                <h2 id="s3" className="font-heading text-xl font-semibold">
                  3. Try it
                </h2>
                <div className="no-print mt-3">
                  <Button
                    icon="board"
                    onClick={() =>
                      navigate("/board", {
                        mode: "steps",
                        title: data.idea.title,
                        s: data.idea.steps.join("|"),
                      })
                    }
                  >
                    Show it on the board
                  </Button>
                </div>
                <dl className="mt-4 grid gap-3 md:grid-cols-3">
                  <div className="rounded-lg bg-bg p-3">
                    <dt className="font-semibold">If kids get stuck</dt>
                    <dd>{data.if_stuck}</dd>
                  </div>
                  <div className="rounded-lg bg-bg p-3">
                    <dt className="font-semibold">If it&apos;s too easy</dt>
                    <dd>{data.if_easy}</dd>
                  </div>
                  <div className="rounded-lg bg-bg p-3">
                    <dt className="font-semibold">For kids learning English</dt>
                    <dd>{data.for_english_learners}</dd>
                  </div>
                </dl>
              </Card>

              <Card aria-labelledby="s4">
                <h2 id="s4" className="font-heading text-xl font-semibold">
                  4. Look back{" "}
                  <span className="text-base font-normal text-muted">(after you try it)</span>
                </h2>
                <div className="mt-3">
                  <RadioChips
                    legend="How many kids could do it?"
                    name="look"
                    value={look}
                    onChange={setLook}
                    options={LOOK.map((d) => ({ value: d, label: d }))}
                  />
                </div>
                <p role="status" className="mt-3 text-muted">
                  {look
                    ? "Thanks for noticing. This stays on your screen only. We don't save it."
                    : "Just for you. We never ask for student names or scores."}
                </p>
              </Card>
            </div>
            <div>
              <SourceList />
            </div>
          </div>
          <p className="mt-4 text-sm text-muted">
            Sample content. Steps and research summary are examples until checked by our content
            lead.
          </p>
        </SourcesScope>
      )}
    </>
  );
}
