import { useEffect, type ReactNode } from "react";
import AdminPage from "./admin/AdminPage";
import { AuthProvider, useAuth } from "./app/auth";
import SignIn from "./screens/auth/SignIn";
import RequestAccess from "./screens/auth/RequestAccess";
import { AcceptInvite, ForgotPassword, ForgotSent, RequestReceived } from "./screens/auth/Simple";
import { flags } from "./app/flags";
import { Shell } from "./app/Shell";
import { Link, match, navigate, PageTitle, useLocation } from "./app/router";
import { SettingsProvider } from "./app/settings";
import { lazy, Suspense } from "react";
import Answer from "./screens/Answer";
import GroupPlan from "./screens/GroupPlan";
import Groups from "./screens/Groups";
import Home from "./screens/Home";
import Refreshers from "./screens/Refreshers";
import SettingsScreen from "./screens/SettingsScreen";
import ClassBoard from "./screens/ClassBoard";
import Stuck from "./screens/Stuck";
import Training from "./screens/Training";
import TrainingTopic from "./screens/TrainingTopic";
import MakeStory from "./screens/MakeStory";

const DesignSheet = import.meta.env.DEV ? lazy(() => import("./dev/DesignSheet")) : null;

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
  if (DesignSheet && path === "/design")
    return {
      node: (
        <Suspense fallback={null}>
          <DesignSheet />
        </Suspense>
      ),
    };
  if (path === "/teaching" || path === "/teaching/groups") return { node: <Groups /> };
  const plan = match("/teaching/groups/:id", path);
  if (plan) return { node: <GroupPlan id={plan.id} /> };
  if (path === "/settings") return { node: <SettingsScreen /> };
  if (path === "/board") return { node: <ClassBoard />, board: true };
  if (path === "/training") return { node: <Training /> };
  if (path === "/training/refreshers") return { node: <Refreshers /> };
  const topic = match("/training/topic/:id", path);
  if (topic) return { node: <TrainingTopic id={topic.id} /> };
  if (path === "/teaching/stuck") return { node: <Stuck /> };
  if (path === "/teaching/story") return { node: <MakeStory /> };
  if (path === "/ask") return { node: <Answer /> };
  if (flags.behavior && path === "/behavior") return { node: <FlaggedOff name="Behavior" /> };
  if (flags.progress && path === "/teaching/progress")
    return { node: <FlaggedOff name="Progress" /> };
  return { node: <NotFound /> };
}

const PUBLIC: Record<string, () => ReactNode> = {
  "/signin": () => <SignIn />,
  "/request-access": () => <RequestAccess />,
  "/request-received": () => <RequestReceived />,
  "/forgot-password": () => <ForgotPassword />,
  "/forgot-sent": () => <ForgotSent />,
  "/accept-invite": () => <AcceptInvite />,
};

function NoAccess() {
  return (
    <>
      <PageTitle title="No access">You don&apos;t have access to this page</PageTitle>
      <p className="mt-3">This page is for administrators.</p>
      <p className="mt-3">
        <Link to="/" className="inline-flex min-h-target items-center text-primary underline">
          Go back to Home
        </Link>
      </p>
    </>
  );
}

function Redirect({ to, query }: { to: string; query?: Record<string, string> }) {
  const q = JSON.stringify(query ?? {});
  useEffect(() => navigate(to, JSON.parse(q)), [to, q]);
  return null;
}

function Routes() {
  const { path, query } = useLocation();
  const { user, checking } = useAuth();
  const pub = PUBLIC[path];

  if (pub) {
    if (user) return <Redirect to="/" />; // already signed in
    return <Shell bare>{pub()}</Shell>;
  }
  if (checking)
    return (
      <Shell bare>
        <p role="status" className="py-10 text-center text-lg">
          Checking your sign-in…
        </p>
      </Shell>
    );
  if (!user) {
    const here = path + (query.toString() ? `?${query}` : "");
    // only plain paths survive as "next" (no query), so it can never become a redirect to elsewhere
    return (
      <Redirect
        to="/signin"
        query={path === "/" ? {} : { next: path.length > 1 ? path : "" }}
        key={here}
      />
    );
  }
  if (path === "/admin")
    return <Shell>{user.role === "admin" ? <AdminPage /> : <NoAccess />}</Shell>;
  const { node, board } = route(path, query);
  return <Shell board={board}>{node}</Shell>;
}

export default function App() {
  return (
    <SettingsProvider>
      <AuthProvider>
        <Routes />
      </AuthProvider>
    </SettingsProvider>
  );
}
