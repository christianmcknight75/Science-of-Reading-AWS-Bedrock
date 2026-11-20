import { PageTitle } from "../app/router";
import { useSettings, type Settings } from "../app/settings";
import { Badge, Card } from "../components/ui";
import { RadioChips } from "../components/RadioChips";
import { ReadAloud } from "../components/ReadAloud";

function Switch({
  id,
  label,
  checked,
  onChange,
}: {
  id: string;
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label
      htmlFor={id}
      className="relative flex min-h-target cursor-pointer items-center justify-between gap-4 rounded-lg border border-control bg-surface px-4 py-2 has-[:focus-visible]:outline has-[:focus-visible]:outline-[3px] has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-primary"
    >
      <span className="font-semibold">{label}</span>
      {/* The real checkbox covers the whole row, so the tap target is the full 48px row. */}
      <input
        id={id}
        type="checkbox"
        role="switch"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="peer absolute inset-0 h-full w-full cursor-pointer opacity-0"
      />
      <span
        aria-hidden="true"
        className={`flex items-center gap-2 rounded-full border-2 border-primary px-3 py-1 font-bold ${checked ? "bg-primary text-white" : "bg-surface text-ink"}`}
      >
        {checked ? "On" : "Off"}
      </span>
    </label>
  );
}

export default function SettingsScreen() {
  const { settings: s, set } = useSettings();
  const preview =
    "Putting sounds together. Kids hear sounds one at a time and say them fast to make a word. Start with 2 sounds, then 3.";
  return (
    <>
      <PageTitle title="Text size and read aloud">Text size and read aloud</PageTitle>
      <p className="mt-2 text-lg text-muted">
        Change how things look and sound. It applies to every screen, and you can change it any
        time.
      </p>
      <div className="mt-5 grid gap-5 lg:grid-cols-2">
        <div className="flex flex-col gap-5">
          <Card aria-labelledby="look">
            <h2 id="look" className="mb-3 font-heading text-xl font-semibold">
              How it looks
            </h2>
            <div className="flex flex-col gap-4">
              <RadioChips<Settings["textSize"]>
                legend="Text size"
                name="size"
                value={s.textSize}
                onChange={(v) => set("textSize", v)}
                options={[
                  { value: "normal", label: "Normal" },
                  { value: "large", label: "Large" },
                  { value: "xl", label: "Extra large" },
                ]}
              />
              <RadioChips<Settings["contrast"]>
                legend="Colors"
                name="contrast"
                value={s.contrast}
                onChange={(v) => set("contrast", v)}
                options={[
                  { value: "standard", label: "Standard" },
                  { value: "high", label: "High contrast" },
                ]}
              />
              <RadioChips<Settings["language"]>
                legend="Language"
                name="lang"
                value={s.language}
                onChange={(v) => set("language", v)}
                options={[
                  { value: "en", label: "English" },
                  { value: "es", label: "Español" },
                ]}
              />
              {s.language === "es" && (
                <p role="status" className="rounded-lg bg-notice-bg p-3 text-notice-text">
                  Spanish is coming later. For now everything is shown in English.
                </p>
              )}
              <RadioChips<"plain" | "both">
                legend="Words"
                name="words"
                value={s.trainingWords ? "both" : "plain"}
                onChange={(v) => set("trainingWords", v === "both")}
                options={[
                  { value: "plain", label: "Plain words only" },
                  { value: "both", label: "Also show training words" },
                ]}
              />
            </div>
          </Card>
          <Card aria-labelledby="sound">
            <h2 id="sound" className="mb-3 font-heading text-xl font-semibold">
              How it sounds and moves
            </h2>
            <div className="flex flex-col gap-3">
              <Switch
                id="ra"
                label="Read answers aloud for me"
                checked={s.readAloud}
                onChange={(v) => set("readAloud", v)}
              />
              <Switch
                id="sh"
                label="Show words with every sound"
                checked={s.soundHints}
                onChange={(v) => set("soundHints", v)}
              />
              <Switch
                id="rm"
                label="Less moving and animation"
                checked={s.reduceMotion}
                onChange={(v) => set("reduceMotion", v)}
              />
            </div>
            <p className="mt-3 text-sm text-muted">
              Read aloud uses your device&apos;s own voice. Nothing you hear is sent anywhere.
            </p>
          </Card>
        </div>
        <Card aria-labelledby="prev" className="self-start">
          <h2 id="prev" className="mb-3 font-heading text-xl font-semibold">
            Preview
          </h2>
          <Badge>Research says</Badge>
          <p className="mt-3 text-lg">{preview}</p>
          <div className="mt-4">
            <ReadAloud text={preview} label="Read aloud" />
          </div>
        </Card>
      </div>
      <p className="mt-4 text-sm text-muted">
        Works with screen readers, keyboard only, and browser zoom.
      </p>
    </>
  );
}
