import { useState, type FormEvent, type ReactNode } from "react";
import { Icon } from "../components/Icon";
import { Button, Card, LinkButton } from "../components/ui";
import { flags } from "../app/flags";
import { Link, navigate, PageTitle } from "../app/router";
import { useGroups } from "../lib/groups";

function Area({
  id,
  icon,
  title,
  blurb,
  links,
  open,
  primary,
}: {
  id: string;
  icon: string;
  title: string;
  blurb: string;
  links: { label: string; to: string; note?: ReactNode }[];
  open: { label: string; to: string };
  primary?: boolean;
}) {
  return (
    <Card
      aria-labelledby={id}
      className={`flex flex-col gap-4 ${primary ? "border-2 border-primary" : ""}`}
    >
      <span className="text-primary">
        <Icon name={icon} className="h-9 w-9" />
      </span>
      <h2 id={id} className="font-heading text-2xl font-semibold">
        {title}
      </h2>
      <p>{blurb}</p>
      <ul className="flex flex-col gap-2">
        {links.map((l) => (
          <li key={l.label}>
            <Link
              to={l.to}
              className="flex min-h-target items-center justify-between gap-2 rounded-lg bg-bg px-3 py-2 font-medium hover:bg-border"
            >
              <span>{l.label}</span>
              {l.note}
            </Link>
          </li>
        ))}
      </ul>
      <LinkButton to={open.to} variant={primary ? "primary" : "secondary"} className="mt-auto">
        {open.label}
      </LinkButton>
    </Card>
  );
}

export default function Home() {
  const [groups] = useGroups();
  const [q, setQ] = useState("");

  function submit(e: FormEvent) {
    e.preventDefault();
    if (q.trim()) navigate("/ask", { q: q.trim() });
  }

  return (
    <>
      <PageTitle title="Home">What do you want to work on?</PageTitle>
      <p className="mt-2 text-lg text-muted">Pick one. You can switch any time from the top bar.</p>

      <div className={`mt-6 grid gap-5 ${flags.behavior ? "lg:grid-cols-3" : "md:grid-cols-2"}`}>
        <Area
          id="area-teaching"
          icon="book"
          title="Teaching"
          primary
          blurb="Plan tomorrow's reading groups, make stories kids can sound out, and figure out why a kid is stuck."
          links={[
            {
              label: "Tomorrow's groups",
              to: "/teaching/groups",
              note: (
                <span className="rounded-full bg-notice-bg px-3 py-1 text-sm font-semibold text-notice-text">
                  {groups.length} {groups.length === 1 ? "group" : "groups"}
                </span>
              ),
            },
            { label: "Make a story", to: "/teaching/story" },
            { label: "Why is a kid stuck?", to: "/teaching/stuck" },
          ]}
          open={{ label: "Open Teaching", to: "/teaching/groups" }}
        />
        <Area
          id="area-training"
          icon="cap"
          title="Training"
          blurb="Turn what you learned in training into this week's plan, and keep it fresh in 1 minute a day."
          links={[
            { label: "My training", to: "/training" },
            { label: "Today's 1-minute refresher", to: "/training/refreshers" },
            { label: "Turn a topic into a plan", to: "/training" },
          ]}
          open={{ label: "Open Training", to: "/training" }}
        />
      </div>

      <form
        onSubmit={submit}
        role="search"
        aria-label="Ask a question"
        className="rh-card mt-6 flex flex-col gap-3 rounded-2xl border border-border bg-surface p-3 sm:flex-row sm:items-center"
      >
        <label htmlFor="just-ask" className="px-2 font-bold">
          Or just ask:
        </label>
        <input
          id="just-ask"
          type="text"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          maxLength={1000}
          autoComplete="off"
          aria-describedby="ask-help"
          placeholder="How do I teach kids the difference between b and d?"
          className="min-h-target flex-1 rounded-lg border border-control bg-surface px-3 text-ink placeholder:text-muted"
        />
        <Button type="submit" variant="primary">
          Ask
        </Button>
      </form>
      <p id="ask-help" className="mt-2 text-sm text-muted">
        Please don&apos;t type student names. Describe what you see instead.
      </p>
    </>
  );
}
