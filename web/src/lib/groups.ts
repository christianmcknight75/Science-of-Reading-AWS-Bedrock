import type { Group } from "../api";
import { DEFAULT_SOUNDS } from "./decode";
import { useStored } from "./storage";

// Labels are free text ("Group A", "Blue table"). We never ask for or store a student name.
export const DEFAULT_GROUPS: Group[] = [
  { id: "g-a", label: "Group A", size: 5, focus: "digraphs" },
  { id: "g-b", label: "Group B", size: 6, focus: "blend" },
  { id: "g-c", label: "Group C", size: 4, focus: "hear-sounds" },
];

export const SKILL_LABEL: Record<Group["focus"], string> = {
  "hear-sounds": "hearing sounds in words",
  blend: "putting sounds together",
  digraphs: "two letters, one sound (sh, ch)",
  "tricky-words": "tricky words",
};

export const useGroups = () => useStored<Group[]>("rh-groups", DEFAULT_GROUPS);
export const useTaughtSounds = () => useStored<string[]>("rh-sounds", DEFAULT_SOUNDS);
