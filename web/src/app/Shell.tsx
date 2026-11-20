import type { ReactNode } from "react";
import { CONTENT_LAST_UPDATED, DISCLAIMER, IS_MOCK } from "../api";
import { Icon, Logo } from "../components/Icon";
import { flags } from "./flags";
import { Link, useLocation } from "./router";

function formatDate(iso: string) {
  const d = new Date(`${iso}T12:00:00`);
  return Number.isNaN(d.getTime())
    ? iso
    : d.toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });
}

const navLink = "inline-flex min-h-target items-center rounded-lg px-4 font-semibold";

function NavItem({ to, active, children }: { to: string; active: boolean; children: ReactNode }) {
  return (
    <Link
      to={to}
      aria-current={active ? "page" : undefined}
      className={`${navLink} rounded-full ${active ? "bg-primary text-white shadow-sm" : "text-ink hover:bg-tint"}`}
    >
      {children}
    </Link>
  );
}

export function Footer({ compact = false }: { compact?: boolean }) {
  return (
    <footer
      className={`border-t border-border bg-surface ${compact ? "px-4 py-3" : "px-4 py-6 sm:px-6"}`}
    >
      <div className="mx-auto flex max-w-6xl flex-col gap-2">
        <p className="rounded-lg bg-notice-bg p-3 text-notice-text" data-testid="disclaimer">
          <strong>Advice only.</strong> {DISCLAIMER}
        </p>
        <p className="text-sm text-muted">
          Content last updated:{" "}
          <time dateTime={CONTENT_LAST_UPDATED}>{formatDate(CONTENT_LAST_UPDATED)}</time>
        </p>
      </div>
    </footer>
  );
}

export function Shell({ children, board = false }: { children: ReactNode; board?: boolean }) {
  const { path } = useLocation();
  const at = (p: string) => (p === "/" ? path === "/" : path.startsWith(p));
  return (
    <div className="flex min-h-screen flex-col">
      <a
        href="#main"
        className="skip-link"
        onClick={(e) => {
          e.preventDefault();
          document.getElementById("main")?.focus();
        }}
      >
        Skip to main content
      </a>
      {!board && (
        <header className="no-print sticky top-0 z-30 border-b border-border bg-surface/95 shadow-card backdrop-blur">
          <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-4 gap-y-2 px-4 py-2 sm:px-6">
            <Link
              to="/"
              className="flex min-h-target items-center gap-2 font-heading text-xl font-semibold"
            >
              <Logo />
              Reading Helper
            </Link>
            <nav aria-label="Main" className="flex flex-1 flex-wrap items-center gap-1">
              <NavItem to="/" active={at("/")}>
                Home
              </NavItem>
              <NavItem to="/teaching/groups" active={at("/teaching")}>
                Teaching
              </NavItem>
              {flags.behavior && (
                <NavItem to="/behavior" active={at("/behavior")}>
                  Behavior
                </NavItem>
              )}
              <NavItem to="/training" active={at("/training")}>
                Training
              </NavItem>
            </nav>
            <Link
              to="/settings"
              aria-current={at("/settings") ? "page" : undefined}
              className={`${navLink} gap-2 rounded-full border border-control ${at("/settings") ? "bg-primary text-white" : "bg-surface hover:bg-tint"}`}
            >
              <Icon name="sliders" />
              Text size &amp; read aloud
            </Link>
          </div>
        </header>
      )}
      {IS_MOCK && !board && (
        <p
          role="note"
          className="no-print bg-highlight px-4 py-2 text-center text-sm font-semibold text-ink"
        >
          Example mode: everything here is sample content so you can try the screens. It is not a
          real answer from the research.
        </p>
      )}
      <main
        id="main"
        tabIndex={-1}
        className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 outline-none sm:px-6"
      >
        {children}
      </main>
      <Footer compact={board} />
    </div>
  );
}
