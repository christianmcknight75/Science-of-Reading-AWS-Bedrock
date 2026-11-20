import { useState } from "react";
import type { Group, Skill } from "../api";
import { Link, PageTitle } from "../app/router";
import { TeachingNav } from "../components/TeachingNav";
import { Button, Card, LinkButton, ToggleChip } from "../components/ui";
import { ALL_SOUNDS } from "../lib/decode";
import { SKILL_LABEL, useGroups, useTaughtSounds } from "../lib/groups";

const SKILLS = Object.keys(SKILL_LABEL) as Skill[];

function SkillSelect({
  id,
  value,
  onChange,
}: {
  id: string;
  value: Skill;
  onChange: (s: Skill) => void;
}) {
  return (
    <select
      id={id}
      value={value}
      onChange={(e) => onChange(e.target.value as Skill)}
      className="min-h-target w-full rounded-lg border border-control bg-surface px-3"
    >
      {SKILLS.map((k) => (
        <option key={k} value={k}>
          {SKILL_LABEL[k]}
        </option>
      ))}
    </select>
  );
}

function EditGroup({
  group,
  onSave,
  onCancel,
  onRemove,
}: {
  group: Group;
  onSave: (g: Group) => void;
  onCancel: () => void;
  onRemove?: () => void;
}) {
  const [label, setLabel] = useState(group.label);
  const [size, setSize] = useState(group.size?.toString() ?? "");
  const [focus, setFocus] = useState<Skill>(group.focus);
  const id = group.id;
  return (
    <form
      className="flex flex-col gap-3"
      onSubmit={(e) => {
        e.preventDefault();
        const n = parseInt(size, 10);
        onSave({
          ...group,
          label: label.trim() || "Group",
          size: Number.isFinite(n) ? n : null,
          focus,
        });
      }}
    >
      <div>
        <label htmlFor={`${id}-label`} className="block font-semibold">
          Group label
        </label>
        <input
          id={`${id}-label`}
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          maxLength={30}
          aria-describedby={`${id}-label-help`}
          className="min-h-target w-full rounded-lg border border-control bg-surface px-3"
        />
        <p id={`${id}-label-help`} className="mt-1 text-sm text-muted">
          A letter or a nickname like &ldquo;Blue table&rdquo;. Please don&apos;t use student names.
        </p>
      </div>
      <div>
        <label htmlFor={`${id}-size`} className="block font-semibold">
          How many kids (optional)
        </label>
        <input
          id={`${id}-size`}
          type="number"
          min={1}
          max={12}
          inputMode="numeric"
          value={size}
          onChange={(e) => setSize(e.target.value)}
          className="min-h-target w-28 rounded-lg border border-control bg-surface px-3"
        />
      </div>
      <div>
        <label htmlFor={`${id}-focus`} className="block font-semibold">
          Working on
        </label>
        <SkillSelect id={`${id}-focus`} value={focus} onChange={setFocus} />
      </div>
      <div className="flex flex-wrap gap-2">
        <Button type="submit" variant="primary">
          Save group
        </Button>
        <Button onClick={onCancel}>Cancel</Button>
        {onRemove && (
          <Button onClick={onRemove} variant="quiet">
            Remove group
          </Button>
        )}
      </div>
    </form>
  );
}

export default function Groups() {
  const [groups, setGroups] = useGroups();
  const [taught, setTaught] = useTaughtSounds();
  const [editing, setEditing] = useState<string | null>(null);
  const [changeSounds, setChangeSounds] = useState(false);
  const known = new Set(taught);

  const save = (g: Group) => {
    setGroups(
      groups.some((x) => x.id === g.id)
        ? groups.map((x) => (x.id === g.id ? g : x))
        : [...groups, g],
    );
    setEditing(null);
  };
  const add = () => {
    const id = `g-${Date.now().toString(36)}`;
    setGroups([
      ...groups,
      { id, label: `Group ${String.fromCharCode(65 + groups.length)}`, size: null, focus: "blend" },
    ]);
    setEditing(id);
  };

  return (
    <>
      <TeachingNav current="/teaching/groups" />
      <PageTitle title="Tomorrow's groups">Tomorrow&apos;s small groups</PageTitle>
      <p className="mt-2 text-lg text-muted">
        {groups.length} {groups.length === 1 ? "group" : "groups"}. Pick what each group is working
        on and we build tomorrow&apos;s plan from it.
      </p>
      {groups.length > 0 && (
        <div className="mt-4">
          <LinkButton to={`/teaching/groups/${groups[0].id}`} variant="primary">
            Plan all {groups.length} {groups.length === 1 ? "group" : "groups"}
          </LinkButton>
        </div>
      )}

      <ul className="mt-5 grid gap-4 md:grid-cols-3">
        {groups.map((g) => (
          <li key={g.id}>
            <Card aria-labelledby={`${g.id}-h`} className="flex h-full flex-col gap-2">
              {editing === g.id ? (
                <>
                  <h2 id={`${g.id}-h`} className="font-heading text-xl font-semibold">
                    Edit {g.label}
                  </h2>
                  <EditGroup
                    group={g}
                    onSave={save}
                    onCancel={() => setEditing(null)}
                    onRemove={() => {
                      setGroups(groups.filter((x) => x.id !== g.id));
                      setEditing(null);
                    }}
                  />
                </>
              ) : (
                <>
                  <h2 id={`${g.id}-h`} className="font-heading text-xl font-semibold">
                    {g.label}
                  </h2>
                  {g.size !== null && <p className="text-muted">{g.size} kids</p>}
                  <p>
                    <strong>Working on:</strong> {SKILL_LABEL[g.focus]}
                  </p>
                  <p className="text-muted">
                    Tomorrow: a short plan for this skill, with a story and a quick check.
                  </p>
                  <div className="mt-auto flex flex-wrap gap-2 pt-2">
                    <LinkButton to={`/teaching/groups/${g.id}`} variant="primary">
                      See plan<span className="sr-only"> for {g.label}</span>
                    </LinkButton>
                    <Button onClick={() => setEditing(g.id)} aria-label={`Edit ${g.label}`}>
                      Edit
                    </Button>
                  </div>
                </>
              )}
            </Card>
          </li>
        ))}
      </ul>
      <div className="mt-4">
        <Button icon="plus" onClick={add}>
          Add a group
        </Button>
      </div>

      <Card aria-labelledby="learned" className="mt-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 id="learned" className="font-heading text-lg font-semibold">
              Sounds your class has learned
            </h2>
            <p className="text-muted">Every word list and story we make uses only these.</p>
          </div>
          <Button onClick={() => setChangeSounds(!changeSounds)} aria-expanded={changeSounds}>
            {changeSounds ? "Done" : "Change"}
          </Button>
        </div>
        {changeSounds ? (
          <div role="group" aria-labelledby="learned" className="mt-3 flex flex-wrap gap-2">
            {ALL_SOUNDS.map((s) => (
              <ToggleChip
                key={s}
                pressed={known.has(s)}
                onClick={() =>
                  setTaught(known.has(s) ? taught.filter((x) => x !== s) : [...taught, s])
                }
              >
                {s}
              </ToggleChip>
            ))}
          </div>
        ) : (
          <ul className="mt-3 flex flex-wrap gap-2" aria-label="Learned sounds">
            {ALL_SOUNDS.filter((s) => known.has(s)).map((s) => (
              <li
                key={s}
                className="flex min-h-target min-w-target items-center justify-center rounded-lg border-2 border-ink px-3 text-lg font-semibold"
              >
                {s}
              </li>
            ))}
          </ul>
        )}
      </Card>

      <div className="mt-6 grid gap-4 md:grid-cols-2">
        <Card aria-labelledby="same-mistake">
          <h2 id="same-mistake" className="font-heading text-lg font-semibold">
            A kid keeps making the same mistake?
          </h2>
          <p className="mt-1 text-muted">
            Type what they read. We&apos;ll find the skill behind it.
          </p>
          <Link
            to="/teaching/stuck"
            className="mt-3 inline-flex min-h-target items-center font-semibold text-primary underline"
          >
            Why is a kid stuck?
          </Link>
        </Card>
        <Card aria-labelledby="need-story">
          <h2 id="need-story" className="font-heading text-lg font-semibold">
            Need a story they can actually read?
          </h2>
          <p className="mt-1 text-muted">Made from only the sounds they know. Free to print.</p>
          <Link
            to="/teaching/story"
            className="mt-3 inline-flex min-h-target items-center font-semibold text-primary underline"
          >
            Make a story
          </Link>
        </Card>
      </div>
      <p className="mt-4 text-sm text-muted">
        Groups use letters or labels, never names. This list stays on this device.
      </p>
    </>
  );
}
