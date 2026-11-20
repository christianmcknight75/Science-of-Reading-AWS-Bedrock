import { useState } from "react";
import { useGroups } from "../lib/groups";
import { useStored } from "../lib/storage";
import { Button } from "./ui";

/** Saves an idea on this device under a group label. Nothing here names a student. */
export function AddToGroup({ title, steps }: { title: string; steps: string[] }) {
  const [groups] = useGroups();
  const [added, setAdded] = useStored<Record<string, { title: string; steps: string[] }[]>>(
    "rh-added",
    {},
  );
  const [open, setOpen] = useState(false);
  const [gid, setGid] = useState(groups[0]?.id ?? "");
  const [done, setDone] = useState<string | null>(null);
  if (!open)
    return (
      <>
        <Button onClick={() => setOpen(true)} aria-expanded={false}>
          Add to a group&apos;s plan
        </Button>
        <span role="status" className="font-semibold">
          {done ? `Added to ${done}\u2019s plan.` : ""}
        </span>
      </>
    );
  return (
    <div className="flex flex-wrap items-end gap-2" role="group" aria-label="Add to a group's plan">
      <div>
        <label htmlFor="which-group" className="block text-sm font-semibold">
          Which group?
        </label>
        <select
          id="which-group"
          value={gid}
          onChange={(e) => setGid(e.target.value)}
          className="min-h-target rounded-lg border border-control bg-surface px-3"
        >
          {groups.map((g) => (
            <option key={g.id} value={g.id}>
              {g.label}
            </option>
          ))}
        </select>
      </div>
      <Button
        variant="primary"
        disabled={!gid}
        onClick={() => {
          setAdded({ ...added, [gid]: [...(added[gid] ?? []), { title, steps }] });
          setDone(groups.find((g) => g.id === gid)?.label ?? "the group");
          setOpen(false);
        }}
      >
        Add
      </Button>
      <Button variant="quiet" onClick={() => setOpen(false)}>
        Cancel
      </Button>
    </div>
  );
}
