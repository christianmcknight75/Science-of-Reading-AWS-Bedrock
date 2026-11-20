import { SubNav } from "./ui";

export function TrainingNav({ current }: { current: string }) {
  return (
    <SubNav
      label="Training"
      current={current}
      items={[
        { label: "My training", to: "/training" },
        { label: "1-minute refreshers", to: "/training/refreshers" },
      ]}
    />
  );
}
