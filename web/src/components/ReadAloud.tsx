import { useEffect } from "react";
import { useSettings } from "../app/settings";
import { useSpeech } from "../app/speech";
import { Button } from "./ui";

/** Reads the given text with the browser's voice. Hidden when the browser has none. */
export function ReadAloud({
  text,
  label = "Read this answer aloud",
}: {
  text: string;
  label?: string;
}) {
  const { speak, stop, speaking, supported } = useSpeech();
  const { settings } = useSettings();
  useEffect(() => {
    if (settings.readAloud && text) speak(text);
  }, [settings.readAloud, text, speak]);
  if (!supported) return null;
  return speaking ? (
    <Button onClick={stop} icon="stop" className="no-print">
      Stop reading
    </Button>
  ) : (
    <Button onClick={() => speak(text)} icon="speaker" className="no-print">
      {label}
    </Button>
  );
}
