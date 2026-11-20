import { useMemo, useState } from "react";
import { makeStory } from "../api";
import { PageTitle } from "../app/router";
import { AddToGroup } from "../components/AddToGroup";
import { Icon } from "../components/Icon";
import { checkStory, MarksLegend, StoryText } from "../components/StoryText";
import { TeachingNav } from "../components/TeachingNav";
import { Badge, Button, Card, ErrorMessage, ExampleChip, ToggleChip } from "../components/ui";
import { ALL_SOUNDS } from "../lib/decode";
import { useTaughtSounds } from "../lib/groups";
import { useAsync } from "../lib/useAsync";
import { useWordChecks } from "../lib/useWordChecks";

export default function MakeStory() {
  const [taught, setTaught] = useTaughtSounds();
  const [about, setAbout] = useState("");
  const [n, setN] = useState(0);
  const known = useMemo(() => new Set(taught), [taught]);
  const { data, error, loading, retry } = useAsync(
    () => makeStory({ sounds: taught, about: about.trim() || undefined, variant: n }),
    `story${n}`,
  );

  // The server's marks come with the story. When the teacher turns a sound on or off, the server
  // checks every word again (plain code, no model); the story itself is not rewritten.
  const recheck = useWordChecks(data?.words ?? [], taught);
  const checks = recheck.checks ?? data?.checks ?? null;
  const { tricky, unknown } = checkStory(data?.words ?? [], known, checks);
  const checking = recheck.loading;

  const toggle = (g: string) =>
    setTaught(known.has(g) ? taught.filter((x) => x !== g) : [...taught, g]);

  return (
    <>
      <TeachingNav current="/teaching/story" />
      <PageTitle>Make a story they can read</PageTitle>
      <p className="mt-2 text-lg text-muted">
        We only use sounds your kids know, then check every word. No searching, no buying books.
      </p>

      <Card aria-labelledby="sounds-legend" className="no-print mt-5">
        <fieldset>
          <legend id="sounds-legend" className="font-heading text-lg font-semibold">
            Sounds they know{" "}
            <span className="text-base font-normal text-muted">
              (tap to turn off and watch the check)
            </span>
          </legend>
          <div className="mt-3 flex flex-wrap gap-2">
            {ALL_SOUNDS.map((g) => (
              <ToggleChip key={g} pressed={known.has(g)} onClick={() => toggle(g)}>
                {g}
              </ToggleChip>
            ))}
          </div>
        </fieldset>
        <form
          className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-end"
          onSubmit={(e) => {
            e.preventDefault();
            setN(n + 1);
          }}
        >
          <div className="flex-1">
            <label htmlFor="about" className="block font-semibold">
              About (optional)
            </label>
            <input
              id="about"
              type="text"
              value={about}
              onChange={(e) => setAbout(e.target.value)}
              maxLength={60}
              placeholder="a pet fish"
              className="mt-1 min-h-target w-full rounded-lg border border-control bg-surface px-3"
            />
          </div>
          <Button type="submit" variant="primary">
            Make a new story
          </Button>
        </form>
      </Card>

      <div aria-live="polite" className="mt-5">
        {loading && (
          <p
            role="status"
            className="rh-pulse rounded-2xl border border-border bg-surface p-6 text-lg"
          >
            Making a story from your sounds and checking every word…
          </p>
        )}
        {error && <ErrorMessage onRetry={retry}>{error}</ErrorMessage>}
        {data && (
          <Card aria-labelledby="story-title">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 id="story-title" className="font-heading text-2xl font-semibold">
                {data.title}
              </h2>
              <div className="flex flex-wrap items-center gap-2">
                {data.example && <ExampleChip />}
                {checking ? (
                  <Badge tone="plain">Checking every word…</Badge>
                ) : unknown === 0 ? (
                  <Badge tone="plain">
                    <Icon name="check" className="mr-1 inline h-4 w-4" />
                    Every word checked
                  </Badge>
                ) : (
                  <Badge tone="idea">
                    <Icon name="alert" className="mr-1 inline h-4 w-4" />
                    {unknown} {unknown === 1 ? "word needs" : "words need"} a new sound
                  </Badge>
                )}
              </div>
            </div>
            <div className="mt-4">
              <StoryText words={data.words} known={known} checks={checks} />
            </div>
            <div className="mt-3">
              <MarksLegend />
            </div>
            <p role="status" className="mt-3">
              {checking
                ? "Checking every word against your sounds…"
                : unknown > 0
                  ? "This story uses a sound your kids don't know yet, so it can't be printed or added to a plan. Make a new story to get one that fits."
                  : tricky.length > 0
                    ? `Checked: every other word uses sounds they know. ${tricky.length} tricky ${tricky.length === 1 ? "word" : "words"} to teach first: ${tricky.join(", ")}.`
                    : "Checked: every word uses sounds they know."}
            </p>
            <div className="no-print mt-4 flex flex-wrap items-end gap-2">
              <Button
                icon="print"
                disabled={unknown > 0 || checking}
                onClick={() => window.print()}
              >
                Print this story
              </Button>
              {unknown === 0 && !checking && (
                <AddToGroup title={data.title} steps={[data.words.join(" ")]} />
              )}
            </div>
          </Card>
        )}
      </div>
      <p className="mt-4 text-sm text-muted">
        Example stories for now. The word checker that runs in the live app is built from your
        class&apos;s sounds.
      </p>
    </>
  );
}
