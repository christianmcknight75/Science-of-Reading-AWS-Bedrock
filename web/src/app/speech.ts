import { useCallback, useEffect, useState } from "react";

// Read-aloud uses the browser's own speech engine: no audio is sent anywhere.
export const speechSupported = () => typeof window !== "undefined" && "speechSynthesis" in window;

export function useSpeech() {
  const [speaking, setSpeaking] = useState(false);
  const stop = useCallback(() => {
    if (!speechSupported()) return;
    window.speechSynthesis.cancel();
    setSpeaking(false);
  }, []);
  const speak = useCallback((text: string) => {
    if (!speechSupported()) return;
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = "en-US";
    u.onend = () => setSpeaking(false);
    u.onerror = () => setSpeaking(false);
    setSpeaking(true);
    window.speechSynthesis.speak(u);
  }, []);
  useEffect(() => stop, [stop]); // stop when the screen goes away
  return { speak, stop, speaking, supported: speechSupported() };
}
