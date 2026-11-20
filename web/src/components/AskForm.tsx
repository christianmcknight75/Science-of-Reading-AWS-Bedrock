import { useState, type FormEvent } from "react";
import { navigate } from "../app/router";
import { Button } from "./ui";

export function AskForm({
  id = "just-ask",
  label = "Or just ask:",
  initial = "",
}: {
  id?: string;
  label?: string;
  initial?: string;
}) {
  const [q, setQ] = useState(initial);
  function submit(e: FormEvent) {
    e.preventDefault();
    if (q.trim()) navigate("/ask", { q: q.trim() });
  }
  return (
    <>
      <form
        onSubmit={submit}
        role="search"
        aria-label="Ask a question"
        className="rh-card flex flex-col gap-3 rounded-2xl border border-border bg-surface p-3 sm:flex-row sm:items-center"
      >
        <label htmlFor={id} className="px-2 font-bold">
          {label}
        </label>
        <input
          id={id}
          type="text"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          maxLength={1000}
          autoComplete="off"
          aria-describedby={`${id}-help`}
          placeholder="How do I teach kids the difference between b and d?"
          className="min-h-target flex-1 rounded-lg border border-control bg-surface px-3 text-ink placeholder:text-muted"
        />
        <Button type="submit" variant="primary">
          Ask
        </Button>
      </form>
      <p id={`${id}-help`} className="mt-2 text-sm text-muted">
        Please don&apos;t type student names. Describe what you see instead.
      </p>
    </>
  );
}
