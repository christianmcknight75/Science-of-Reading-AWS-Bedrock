import { useState } from "react";
import { useLocation } from "../app/router";
import { Icon } from "../components/Icon";
import { Button } from "../components/ui";
import { useSpeech } from "../app/speech";

/** Projector view: big type, 64px targets, one thing on screen at a time. */
export default function ClassBoard() {
  const { query } = useLocation();
  const title = query.get("title") ?? "Class board";
  const group = query.get("group");
  const skill = query.get("skill");
  const words = (query.get("words") ?? "").split(",").filter(Boolean);
  const steps = (query.get("s") ?? "").split("|").filter(Boolean);
  const items = query.get("mode") === "steps" ? steps : words;
  const isWords = query.get("mode") !== "steps";
  const [i, setI] = useState(0);
  const [shown, setShown] = useState(false);
  const { speak, supported } = useSpeech();
  const cur = items[i] ?? "";
  const letters = isWords ? [...cur] : [];

  const go = (n: number) => {
    setI(Math.max(0, Math.min(items.length - 1, n)));
    setShown(false);
  };
  return (
    <div className="flex flex-1 flex-col gap-6 px-6 py-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-heading text-4xl font-semibold" tabIndex={-1}>
            {title}
          </h1>
          {(group || skill) && (
            <p className="text-xl text-muted">
              {group}
              {group && skill ? " · " : ""}
              {skill}
            </p>
          )}
        </div>
        <div className="flex items-center gap-4">
          {items.length > 0 && (
            <p className="text-xl font-semibold" role="status">
              {isWords ? "Word" : "Step"} {i + 1} of {items.length}
            </p>
          )}
          <Button size="classroom" icon="close" onClick={() => window.history.back()}>
            Exit board
          </Button>
        </div>
      </div>

      {items.length === 0 ? (
        <p className="text-2xl">Nothing to show here yet. Go back and pick a plan or an idea.</p>
      ) : isWords ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-8 text-center">
          <p className="text-2xl text-muted">Listen to the robot…</p>
          <ul className="flex flex-wrap justify-center gap-4" aria-label="Sounds in the word">
            {letters.map((l, k) => (
              <li
                key={k}
                className="flex h-28 min-w-28 items-center justify-center rounded-2xl border-4 border-ink bg-surface px-4 font-heading text-7xl font-semibold"
              >
                /{l}/
              </li>
            ))}
            {!shown && (
              <li
                className="flex h-28 min-w-28 items-center justify-center text-7xl"
                aria-label="Word hidden"
              >
                ?
              </li>
            )}
          </ul>
          {shown && (
            <p className="font-heading text-8xl font-semibold" aria-live="polite">
              {cur}
            </p>
          )}
          <p className="max-w-3xl text-2xl">
            Say each sound with a short pause. Then: &ldquo;Everyone, on my tap… what word?&rdquo;
          </p>
          {supported && (
            <Button size="classroom" icon="speaker" onClick={() => speak(cur)}>
              Say the word
            </Button>
          )}
        </div>
      ) : (
        <div className="flex flex-1 items-center justify-center">
          <p
            className="max-w-4xl text-center font-heading text-5xl leading-tight"
            aria-live="polite"
          >
            {cur}
          </p>
        </div>
      )}

      {items.length > 0 && (
        <div className="flex flex-wrap justify-center gap-4">
          <Button size="classroom" icon="left" disabled={i === 0} onClick={() => go(i - 1)}>
            Back
          </Button>
          {isWords && (
            <Button size="classroom" variant="secondary" onClick={() => setShown(!shown)}>
              {shown ? "Hide the word" : "Show the word"}
            </Button>
          )}
          <Button
            size="classroom"
            variant="primary"
            disabled={i === items.length - 1}
            onClick={() => go(i + 1)}
          >
            {isWords ? "Next word" : "Next step"}
            <Icon name="right" />
          </Button>
        </div>
      )}
    </div>
  );
}
