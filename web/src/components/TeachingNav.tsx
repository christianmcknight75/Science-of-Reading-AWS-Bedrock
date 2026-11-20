import { flags } from "../app/flags";
import { SubNav } from "./ui";

export function TeachingNav({ current }: { current: string }) {
  const items = [
    { label: "Tomorrow", to: "/teaching/groups" },
    { label: "Make a story", to: "/teaching/story" },
    { label: "Why is a kid stuck?", to: "/teaching/stuck" },
    ...(flags.progress ? [{ label: "Progress", to: "/teaching/progress" }] : []),
  ];
  return <SubNav label="Teaching" items={items} current={current} />;
}
