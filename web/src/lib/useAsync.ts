import { useEffect, useMemo, useState } from "react";
import { ApiError } from "../api";

interface Result<T> {
  token: object;
  data: T | null;
  error: string | null;
}

/** Runs `fn` when `key` changes (or on retry). `loading` is true until that run answers. */
export function useAsync<T>(fn: () => Promise<T>, key: string) {
  const [tick, setTick] = useState(0);
  const token = useMemo(() => ({}), [key, tick]); // eslint-disable-line react-hooks/exhaustive-deps
  const [res, setRes] = useState<Result<T> | null>(null);

  useEffect(() => {
    let live = true;
    fn().then(
      (data) => live && setRes({ token, data, error: null }),
      (e: unknown) =>
        live &&
        setRes({
          token,
          data: null,
          error:
            e instanceof ApiError
              ? e.message
              : "Something went wrong. Please try again in a moment.",
        }),
    );
    return () => {
      live = false;
    };
  }, [token]); // eslint-disable-line react-hooks/exhaustive-deps

  const current = res && res.token === token ? res : null;
  return {
    data: current?.data ?? null,
    error: current?.error ?? null,
    loading: current === null,
    retry: () => setTick((t) => t + 1),
  };
}
