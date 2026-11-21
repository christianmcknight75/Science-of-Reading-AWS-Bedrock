import { useState } from "react";
import { listTrainingTopics, type TrainingTopic } from "../api";
import { Link, navigate, PageTitle } from "../app/router";
import { useSettings } from "../app/settings";
import { TrainingNav } from "../components/TrainingNav";
import { Button, Card, ErrorMessage, LinkButton } from "../components/ui";
import { useAsync } from "../lib/useAsync";

const KEYWORDS: [RegExp, string][] = [
  [/segment|break.*sound|tap|hear.*sound|phonemic/i, "segmenting"],
  [/digraph|\bsh\b|\bch\b|\bth\b|two letters/i, "digraphs"],
  [/cueing|cue|guess|picture|msv/i, "letters-not-pictures"],
];

function TopicCard({ t }: { t: TrainingTopic }) {
  const { settings } = useSettings();
  return (
    <li>
      <Card as="article" aria-labelledby={`t-${t.id}`} className="flex h-full flex-col gap-2">
        <p className="text-sm font-bold text-primary">{t.fits}</p>
        <h3 id={`t-${t.id}`} className="font-heading text-xl font-semibold">
          {t.title}
        </h3>
        <p>
          {t.summary}
          {settings.trainingWords && (
            <span className="text-muted"> (Training word: {t.training_word})</span>
          )}
        </p>
        <div className="mt-auto pt-2">
          <LinkButton to={`/training/topic/${t.id}`} variant="primary">
            Turn into a plan<span className="sr-only">: {t.title}</span>
          </LinkButton>
        </div>
      </Card>
    </li>
  );
}

export default function Training() {
  const { data, error, loading, retry } = useAsync(listTrainingTopics, "topics");
  const [tell, setTell] = useState("");
  const [miss, setMiss] = useState(false);

  return (
    <>
      <TrainingNav current="/training" />
      <PageTitle title="My training">Turn your training into practice</PageTitle>
      <p className="mt-2 text-lg text-muted">
        Pick one idea from training. We turn it into a plan for this week.
      </p>

      <section aria-labelledby="picks" className="mt-5">
        <h2 id="picks" className="font-heading text-xl font-semibold">
          Good next picks for your groups
        </h2>
        <div aria-live="polite" className="mt-3">
          {loading && (
            <p role="status" className="rh-pulse rounded-2xl border border-border bg-surface p-6">
              Loading topics…
            </p>
          )}
          {error && <ErrorMessage onRetry={retry}>{error}</ErrorMessage>}
          {data && (
            <ul className="grid gap-4 md:grid-cols-3">
              {data.map((t) => (
                <TopicCard key={t.id} t={t} />
              ))}
            </ul>
          )}
        </div>
      </section>

      <Card aria-labelledby="add" className="mt-6">
        <h2 id="add" className="font-heading text-xl font-semibold">
          Add something from training
        </h2>
        <p className="mt-1 text-muted">
          Any training works. We put it in plain words and match it to research.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <Button disabled>Photo of my notes (coming soon)</Button>
          <Button disabled>Upload slides (coming soon)</Button>
        </div>
        <form
          className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-end"
          onSubmit={(e) => {
            e.preventDefault();
            const hit = KEYWORDS.find(([re]) => re.test(tell));
            if (hit) navigate(`/training/topic/${hit[1]}`);
            else setMiss(true);
          }}
        >
          <div className="flex-1">
            <label htmlFor="tell" className="block font-semibold">
              Just tell us what you learned
            </label>
            <input
              id="tell"
              value={tell}
              onChange={(e) => {
                setTell(e.target.value);
                setMiss(false);
              }}
              maxLength={200}
              placeholder="We learned about segmenting"
              className="mt-1 min-h-target w-full rounded-lg border border-control bg-surface px-3"
            />
          </div>
          <Button type="submit" variant="primary" disabled={!tell.trim()}>
            Find a plan
          </Button>
        </form>
        <p role="status" className="mt-2">
          {miss
            ? "I couldn't match that to a topic yet. Try one of the picks above, or ask a question from Home."
            : ""}
        </p>
      </Card>

      <Card
        aria-labelledby="refresher"
        className="mt-6 flex flex-wrap items-center justify-between gap-3"
      >
        <div>
          <h2 id="refresher" className="font-heading text-lg font-semibold">
            Today&apos;s refresher
          </h2>
          <p className="text-muted">One true-or-not question. Answer in 1 minute.</p>
        </div>
        <LinkButton to="/training/refreshers">Answer in 1 minute</LinkButton>
      </Card>
      <p className="mt-4 text-sm text-muted">
        <Link to="/ask" className="inline-flex min-h-target items-center text-primary underline">
          Or ask a question
        </Link>
      </p>
    </>
  );
}
