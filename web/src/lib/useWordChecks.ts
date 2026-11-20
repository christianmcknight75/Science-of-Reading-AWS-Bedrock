import { checkDecodable, type WordCheck } from "../api";
import { useAsync } from "./useAsync";

/**
 * The server's word check (CMU dictionary + grapheme rules, plain code) for these words and the
 * sounds the class knows. Runs again whenever the sounds or words change. `checks` is null until
 * the first answer, or when there are no words.
 */
export function useWordChecks(words: string[], sounds: string[]) {
  const letters = words.map((w) => w.replace(/[^A-Za-z']/g, "")).filter(Boolean);
  const key = `wc:${sounds.join(",")}:${letters.join(" ")}`;
  const { data, loading, error } = useAsync<WordCheck[] | null>(
    () => (letters.length ? checkDecodable({ sounds, words: letters }) : Promise.resolve(null)),
    key,
  );
  return { checks: data, loading: loading && letters.length > 0, error };
}
