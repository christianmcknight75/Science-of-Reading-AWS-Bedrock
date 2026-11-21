// Small, illustrative word helpers for the UI (mock mode and the class board).
// The authoritative decodability checker is Phase 4 and runs on the server
// (CMU Pronouncing Dictionary + grapheme rules). Do not rely on this file for real checks.

export const ALL_SOUNDS = [
  "m",
  "s",
  "a",
  "t",
  "p",
  "i",
  "n",
  "f",
  "d",
  "h",
  "c",
  "k",
  "r",
  "o",
  "u",
  "g",
  "l",
  "b",
  "e",
  "sh",
  "ch",
  "th",
] as const;

export const DEFAULT_SOUNDS = ["m", "s", "a", "t", "p", "i", "n", "f", "d", "h", "sh"];

/** Heart words: allowed in a story only from this explicit list, and flagged "teach first". */
export const HEART_WORDS = new Set(["a", "the", "to", "of", "was", "said", "you", "i", "my", "is"]);

const DIGRAPHS = ["sh", "ch", "th"];

/** Split a word into graphemes (digraphs first, then single letters). */
export function graphemes(word: string): string[] {
  const w = word.toLowerCase().replace(/[^a-z]/g, "");
  const out: string[] = [];
  for (let i = 0; i < w.length;) {
    const two = w.slice(i, i + 2);
    if (DIGRAPHS.includes(two)) {
      out.push(two);
      i += 2;
    } else {
      out.push(w[i]);
      i += 1;
    }
  }
  return out;
}

export function unknownSounds(word: string, known: Set<string>): string[] {
  if (HEART_WORDS.has(word.toLowerCase().replace(/[^a-z]/g, ""))) return [];
  return graphemes(word).filter((g) => !known.has(g));
}

export type WordStatus = "ok" | "tricky" | "unknown";

export function checkWord(word: string, known: Set<string>): WordStatus {
  const bare = word.toLowerCase().replace(/[^a-z]/g, "");
  if (HEART_WORDS.has(bare)) return "tricky";
  return unknownSounds(bare, known).length ? "unknown" : "ok";
}

export const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? "" : "s"}`;

/** Mock-only guess at why a child misread a word. Returns a pattern key or null. */
export function classifyPair(
  word: string,
  said: string,
): "digraph" | "blend" | "vowel" | "guess" | null {
  const w = word.toLowerCase().trim();
  const s = said.toLowerCase().trim();
  if (!w || !s || w === s) return null;
  if (/(sh|ch|th)/.test(w) && !/(sh|ch|th)/.test(s)) return "digraph";
  if (s.length < w.length && w.length - s.length <= 2 && [...s].every((c) => w.includes(c)))
    return "blend";
  if (s.length === w.length) {
    const diff = [...w].filter((c, i) => c !== s[i]);
    if (diff.length === 1 && /[aeiou]/.test(diff[0])) return "vowel";
  }
  if (!w.startsWith(s[0]) && ![...s].some((c) => w.includes(c))) return "guess";
  return null;
}
