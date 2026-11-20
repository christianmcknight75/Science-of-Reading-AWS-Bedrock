import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

export interface Settings {
  textSize: "normal" | "large" | "xl";
  contrast: "standard" | "high";
  language: "en" | "es";
  trainingWords: boolean; // also show the training jargon next to plain words
  readAloud: boolean; // read answers aloud automatically
  soundHints: boolean; // show a sound hint with letters ("m" as in moon)
  reduceMotion: boolean;
}

export const DEFAULTS: Settings = {
  textSize: "normal",
  contrast: "standard",
  language: "en",
  trainingWords: false,
  readAloud: false,
  soundHints: true,
  reduceMotion: false,
};

const KEY = "rh-settings";

function load(): Settings {
  try {
    const raw = window.localStorage.getItem(KEY);
    if (raw) return { ...DEFAULTS, ...JSON.parse(raw) };
  } catch {
    /* storage can be blocked; fall back to defaults */
  }
  return DEFAULTS;
}

interface Ctx {
  settings: Settings;
  set: <K extends keyof Settings>(key: K, value: Settings[K]) => void;
}
const SettingsContext = createContext<Ctx | null>(null);

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<Settings>(load);

  useEffect(() => {
    const el = document.documentElement;
    el.dataset.textSize = settings.textSize;
    el.dataset.contrast = settings.contrast;
    el.dataset.motion = settings.reduceMotion ? "reduce" : "auto";
    try {
      window.localStorage.setItem(KEY, JSON.stringify(settings));
    } catch {
      /* ignore */
    }
  }, [settings]);

  const value = useMemo<Ctx>(
    () => ({ settings, set: (k, v) => setSettings((s) => ({ ...s, [k]: v })) }),
    [settings],
  );
  return <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>;
}

export function useSettings(): Ctx {
  const c = useContext(SettingsContext);
  if (!c) throw new Error("useSettings needs SettingsProvider");
  return c;
}
