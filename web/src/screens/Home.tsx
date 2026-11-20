import type { ReactNode } from "react";
import { Icon } from "../components/Icon";
import { AskForm } from "../components/AskForm";
import { Mascot } from "../components/Mascot";
import { Card, LinkButton } from "../components/ui";
import { flags } from "../app/flags";
import { Link, PageTitle } from "../app/router";
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
      interactive
      tone={primary ? "tint" : "plain"}
      className={`flex flex-col gap-4 ${primary ? "border-2 border-primary" : ""}`}
    >
      <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary text-white shadow-sm">
        <Icon name={icon} className="h-8 w-8" />
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
              className="flex min-h-target flex-wrap items-center justify-between gap-x-2 rounded-xl border border-transparent bg-surface px-4 py-2 font-medium shadow-sm hover:border-primary"
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

function greeting() {
  const h = new Date().getHours();
  return h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening";
}

export default function Home() {
  const [groups] = useGroups();

  return (
    <>
      <Card tone="warm" aria-labelledby="greeting" className="rh-rise !p-6 sm:!p-8">
        <div className="flex flex-col items-start gap-5 sm:flex-row sm:items-center">
          <Mascot size={132} className="shrink-0" />
          <div className="min-w-0 flex-1">
            <p className="eyebrow">{greeting()}</p>
            <div id="greeting">
              <PageTitle title="Home">What do you want to work on?</PageTitle>
            </div>
            <p className="mt-2 text-lg text-muted">
              Pick one below, or ask a question. You can switch any time from the top bar.
            </p>
          </div>
        </div>
        <div className="mt-6">
          <AskForm />
        </div>
      </Card>

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
    </>
  );
}
