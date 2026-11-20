import { useEffect, useRef, useSyncExternalStore, type AnchorHTMLAttributes } from "react";

// Tiny hash router: static hosting (S3 + CloudFront) needs no rewrite rules, and the admin
// page already lives at #/admin.
export interface Loc {
  path: string;
  query: URLSearchParams;
}

const subscribe = (cb: () => void) => {
  window.addEventListener("hashchange", cb);
  return () => window.removeEventListener("hashchange", cb);
};
const snapshot = () => window.location.hash;

export function useLocation(): Loc {
  const hash = useSyncExternalStore(subscribe, snapshot);
  const [path, q] = hash.replace(/^#/, "").split("?");
  return { path: path || "/", query: new URLSearchParams(q ?? "") };
}

export function href(path: string, query?: Record<string, string | undefined>) {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(query ?? {})) if (v) q.set(k, v);
  const s = q.toString();
  return `#${path}${s ? `?${s}` : ""}`;
}

export function navigate(path: string, query?: Record<string, string | undefined>) {
  window.location.hash = href(path, query);
}

export function Link({
  to,
  query,
  ...rest
}: { to: string; query?: Record<string, string | undefined> } & Omit<
  AnchorHTMLAttributes<HTMLAnchorElement>,
  "href"
>) {
  return <a href={href(to, query)} {...rest} />;
}

/** "/teaching/groups/:id" style matching. Returns params or null. */
export function match(pattern: string, path: string): Record<string, string> | null {
  const a = pattern.split("/");
  const b = path.split("/");
  if (a.length !== b.length) return null;
  const params: Record<string, string> = {};
  for (let i = 0; i < a.length; i++) {
    if (a[i].startsWith(":")) params[a[i].slice(1)] = decodeURIComponent(b[i]);
    else if (a[i] !== b[i]) return null;
  }
  return params;
}

let lastHash: string | null = null; // only move focus when the page really changed
/**
 * The page's h1. Sets the document title, and moves focus to the heading when the screen
 * changes so keyboard and screen-reader users start at the top of the new page.
 */
export function PageTitle({ children, title }: { children: string; title?: string }) {
  const ref = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    document.title = `${title ?? children} · Reading Helper`;
    const h = window.location.hash;
    if (lastHash !== null && lastHash !== h) ref.current?.focus();
    lastHash = h;
  }, [children, title]);
  return (
    <h1 ref={ref} tabIndex={-1} className="font-heading text-3xl font-semibold leading-tight">
      {children}
    </h1>
  );
}
