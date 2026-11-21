import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { getMe, getToken, signIn as apiSignIn, signOutApi, type Me } from "../api";

interface AuthCtx {
  user: Me | null;
  /** true until we know whether a saved token is still good */
  checking: boolean;
  signIn: (email: string, password: string) => Promise<Me>;
  adopt: (user: Me) => void;
  signOut: () => Promise<void>;
}
const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Me | null>(null);
  const [checking, setChecking] = useState<boolean>(() => getToken() !== null);

  useEffect(() => {
    if (!getToken()) return;
    let live = true;
    getMe().then(
      (u) => {
        if (live) {
          setUser(u);
          setChecking(false);
        }
      },
      () => {
        if (live) setChecking(false);
      },
    );
    return () => {
      live = false;
    };
  }, []);

  // The client fires this when the server says 401 (expired or revoked token).
  useEffect(() => {
    const out = () => setUser(null);
    window.addEventListener("rh-signed-out", out);
    return () => window.removeEventListener("rh-signed-out", out);
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    const r = await apiSignIn(email, password);
    // real client: store the token here; mock stores its own in signIn
    setUser(r.user);
    return r.user;
  }, []);
  const signOut = useCallback(async () => {
    try {
      await signOutApi();
    } catch {
      /* even if the server call fails we sign out on this device */
    }
    setUser(null);
  }, []);

  const value = useMemo<AuthCtx>(
    () => ({ user, checking, signIn, adopt: setUser, signOut }),
    [user, checking, signIn, signOut],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth(): AuthCtx {
  const c = useContext(Ctx);
  if (!c) throw new Error("useAuth needs AuthProvider");
  return c;
}

/** Only same-app hash paths: never a full URL (no open redirect). */
export function safeNext(next: string | null): string {
  return next && /^\/[A-Za-z0-9/_-]*$/.test(next) && !next.startsWith("//") ? next : "/";
}
