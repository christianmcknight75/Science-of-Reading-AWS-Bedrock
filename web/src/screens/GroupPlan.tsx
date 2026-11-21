import { useMemo, useState } from "react";
import { getGroupPlan, type PlanStep } from "../api";
import { Link, navigate, PageTitle } from "../app/router";
import { EvidenceLabel } from "../components/EvidenceLabel";
import { Citations, SourceList, SourcesScope } from "../components/Sources";
import { checkStory, MarksLegend, StoryText } from "../components/StoryText";
import { TeachingNav } from "../components/TeachingNav";
import { Badge, Breadcrumb, Button, Card, ErrorMessage, ExampleChip } from "../components/ui";
import { SKILL_LABEL, useGroups, useTaughtSounds } from "../lib/groups";
import { useStored } from "../lib/storage";
import { useAsync } from "../lib/useAsync";
import { useWordChecks } from "../lib/useWordChecks";

function Step({
  n,
  step,
  known,
  label,
}: {
  n: number;
  step: PlanStep;
  known: Set<string>;
  label: string;
}) {
  const [swapped, setSwapped] = useState(false);
  const title = swapped && step.alt ? step.alt.title : step.title;
  const body = swapped && step.alt ? step.alt.body : step.body;
  const isQuick = step.title === "Quick check";
  const { checks } = useWordChecks(step.story ?? [], [...known]);
  const story = step.story ? checkStory(step.story, known, checks) : null;
  return (
    <li>
      <Card
        as="article"
        aria-labelledby={`step-${n}`}
        className="grid gap-3 sm:grid-cols-[5rem_1fr]"
      >
        <div>
          <p className="font-heading text-2xl font-semibold" aria-hidden="true">
            {n}
          </p>
          <p className="text-sm text-muted">{step.minutes} min</p>
        </div>
        <div className="flex flex-col gap-3">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <h3 id={`step-${n}`} className="font-heading text-xl font-semibold">
              <span className="sr-only">Step {n}, </span>
              {title}
              <span className="sr-only">, {step.minutes} minutes</span>
            </h3>
            {step.alt && (
              <Button
                onClick={() => setSwapped(!swapped)}
                aria-label={swapped ? undefined : `Swap this step: ${title}`}
              >
                {swapped ? "Back to the first idea" : "Swap this step"}
              </Button>
            )}
          </div>
          <p>{body}</p>
          {step.sounds && (
            <ul className="flex flex-wrap gap-2" aria-label="Sounds to flash">
              {step.sounds.map((s) => (
                <li
                  key={s}
                  className="flex min-h-target min-w-target items-center justify-center rounded-lg border-2 border-ink px-3 text-xl font-semibold"
                >
                  {s}
                </li>
              ))}
            </ul>
          )}
          {step.words && (
            <p className="text-lg font-semibold" aria-label={`Words: ${step.words.join(", ")}`}>
              {step.words.join(" · ")}
            </p>
          )}
          {story && (
            <>
              <div className="rounded-lg border border-border bg-notice-bg p-4">
                <StoryText
                  words={step.story!}
                  known={known}
                  checks={checks}
                  className="text-2xl leading-[2.4rem]"
                />
              </div>
              <MarksLegend />
              <p role="status">
                {story.unknown > 0
                  ? `Careful: ${story.unknown} ${story.unknown === 1 ? "word uses" : "words use"} a sound not in your class's list.`
                  : `Checked: every word uses sounds ${label} knows.${story.tricky.length ? ` ${story.tricky.length} tricky ${story.tricky.length === 1 ? "word" : "words"} to teach first: ${story.tricky.join(", ")}.` : ""}`}
              </p>
              <Link
                to="/teaching/story"
                className="inline-flex min-h-target items-center font-semibold text-primary underline"
              >
                Make a different story
              </Link>
            </>
          )}
          {isQuick && (
            <p className="text-muted">
              Just notice how many of the group can read each word. We don&apos;t save this. Use it
              to decide what comes next.
            </p>
          )}
          {step.tip && <p className="rounded-lg bg-bg p-3 text-sm">{step.tip}</p>}
        </div>
      </Card>
    </li>
  );
}

export default function GroupPlan({ id }: { id: string }) {
  const [groups] = useGroups();
  const [taught] = useTaughtSounds();
  const [added, setAdded] = useStored<Record<string, { title: string; steps: string[] }[]>>(
    "rh-added",
    {},
  );
  const group = groups.find((g) => g.id === id);
  const known = useMemo(() => new Set(taught), [taught]);
  const { data, error, loading, retry } = useAsync(
    () => (group ? getGroupPlan(group.focus, taught) : Promise.reject(new Error("no group"))),
    `${id}:${group?.focus}:${taught.join(",")}`,
  );

  if (!group)
    return (
      <>
        <PageTitle title="Group not found">We couldn&apos;t find that group</PageTitle>
        <p className="mt-3">
          <Link
            to="/teaching/groups"
            className="inline-flex min-h-target items-center text-primary underline"
          >
            Back to Tomorrow&apos;s groups
          </Link>
        </p>
      </>
    );

  const mine = added[id] ?? [];
  const boardStep = data?.steps.find((s) => s.words && s.title !== "Quick check");
  return (
    <>
      <TeachingNav current="/teaching/groups" />
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Breadcrumb
          items={[
            { label: "Tomorrow's groups", to: "/teaching/groups" },
            { label: `${group.label} plan` },
          ]}
        />
        <nav aria-label="Switch group" className="flex flex-wrap gap-2">
          {groups.map((g) => (
            <Link
              key={g.id}
              to={`/teaching/groups/${g.id}`}
              aria-current={g.id === id ? "page" : undefined}
              className={`inline-flex min-h-target items-center rounded-lg px-4 font-semibold ${g.id === id ? "bg-ink text-white" : "border border-control bg-surface"}`}
            >
              {g.label}
            </Link>
          ))}
        </nav>
      </div>

      <div className="mt-2 flex flex-wrap items-start justify-between gap-4">
        <div>
          <PageTitle title={`${group.label} plan`}>
            {data ? `${group.label} · ${data.minutes} minutes` : group.label}
          </PageTitle>
          <p className="mt-1 text-lg text-muted">
            {SKILL_LABEL[group.focus][0].toUpperCase() + SKILL_LABEL[group.focus].slice(1)}.
            Everything you need is on this page.
          </p>
        </div>
        {data && (
          <div className="no-print flex flex-wrap gap-2">
            <Button
              variant="primary"
              icon="board"
              onClick={() =>
                navigate("/board", {
                  mode: "words",
                  title: boardStep?.title ?? "Class board",
                  group: group.label,
                  skill: SKILL_LABEL[group.focus],
                  words: (boardStep?.words ?? []).join(","),
                })
              }
            >
              Show on the class board
            </Button>
            <Button icon="print" onClick={() => window.print()}>
              Print this plan
            </Button>
          </div>
        )}
      </div>

      <div aria-live="polite" className="mt-4">
        {loading && (
          <p
            role="status"
            className="rh-pulse rounded-2xl border border-border bg-surface p-6 text-lg"
          >
            Building {group.label}&apos;s plan from the research…
          </p>
        )}
        {error && <ErrorMessage onRetry={retry}>{error}</ErrorMessage>}
        {data && (
          <SourcesScope sources={data.sources} example={!!data.example}>
            <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_20rem]">
              <div className="flex flex-col gap-5">
                <Card aria-labelledby="why" className="border-2 border-primary">
                  <div className="flex flex-wrap items-center gap-3">
                    <h2 id="why" className="m-0">
                      <Badge>Research says</Badge>
                    </h2>
                    <EvidenceLabel label={data.evidence_label} />
                    {data.example && <ExampleChip />}
                  </div>
                  <ul className="mt-3 flex flex-col gap-2">
                    {data.research_says.map((c) => (
                      <li key={c.text} className="flex flex-wrap items-center gap-x-2">
                        <span>{c.text}</span>
                        <Citations ns={c.citations} />
                      </li>
                    ))}
                  </ul>
                  <p className="mt-3">
                    <strong>Why this plan:</strong> {data.why}
                  </p>
                </Card>

                <section aria-labelledby="idea-steps" className="flex flex-col gap-3">
                  <div className="flex flex-wrap items-center gap-3">
                    <h2 id="idea-steps" className="m-0">
                      <Badge tone="idea">Idea for your class</Badge>
                    </h2>
                    <p className="text-sm text-muted">
                      Our suggestion, based on the research above. These steps are not themselves
                      research findings.
                    </p>
                  </div>
                  <ol className="flex flex-col gap-4">
                    {data.steps.map((s, i) => (
                      <Step key={s.title} n={i + 1} step={s} known={known} label={group.label} />
                    ))}
                  </ol>
                </section>

                {mine.length > 0 && (
                  <Card aria-labelledby="mine">
                    <h2 id="mine" className="font-heading text-xl font-semibold">
                      Ideas you added to {group.label}
                    </h2>
                    <ul className="mt-3 flex flex-col gap-3">
                      {mine.map((m, i) => (
                        <li
                          key={`${m.title}-${i}`}
                          className="flex flex-wrap items-start justify-between gap-3 border-t border-border pt-3 first:border-0 first:pt-0"
                        >
                          <div>
                            <p className="font-semibold">{m.title}</p>
                            <p>{m.steps.join(" ")}</p>
                          </div>
                          <Button
                            onClick={() =>
                              setAdded({ ...added, [id]: mine.filter((_, j) => j !== i) })
                            }
                            aria-label={`Remove idea: ${m.title}`}
                          >
                            Remove
                          </Button>
                        </li>
                      ))}
                    </ul>
                  </Card>
                )}
              </div>
              <div>
                <SourceList />
              </div>
            </div>
          </SourcesScope>
        )}
      </div>
      <p className="mt-4 text-sm text-muted">
        Sample content. Steps are ideas based on the research; the story checker and word lists are
        built from your class&apos;s sounds.
      </p>
    </>
  );
}
