import type { ReactNode } from "react";
import AdminReview from "./admin/AdminReview";
import { flags } from "./app/flags";
import { Shell } from "./app/Shell";
import { Link, match, PageTitle, useLocation } from "./app/router";
import { SettingsProvider } from "./app/settings";
import Answer from "./screens/Answer";
import Home from "./screens/Home";

function NotFound() {
  return (
    <>
      <PageTitle title="Page not found">We couldn&apos;t find that page</PageTitle>
      <p className="mt-3">
        <Link to="/" className="text-primary underline">
          Go back to Home
        </Link>
      </p>
    </>
  );
}

function FlaggedOff({ name }: { name: string }) {
  return (
    <>
      <PageTitle>{name}</PageTitle>
      <p className="mt-3">This part of Reading Helper is not ready yet.</p>
    </>
  );
}

function route(path: string, query: URLSearchParams): { node: ReactNode; board?: boolean } {
  void query;
  if (path === "/") return { node: <Home /> };
  if (path === "/ask") return { node: <Answer /> };
  if (flags.behavior && path === "/behavior") return { node: <FlaggedOff name="Behavior" /> };
  if (flags.progress && path === "/teaching/progress")
    return { node: <FlaggedOff name="Progress" /> };
  void match;
  return { node: <NotFound /> };
}

export default function App() {
  const { path, query } = useLocation();
  if (path === "/admin") return <AdminReview />;
  const { node, board } = route(path, query);
  return (
    <SettingsProvider>
      <Shell board={board}>{node}</Shell>
    </SettingsProvider>
  );
}
