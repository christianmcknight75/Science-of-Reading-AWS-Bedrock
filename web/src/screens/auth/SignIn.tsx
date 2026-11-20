import { useRef, useState, type FormEvent } from "react";
import { ApiError, IS_MOCK, MOCK_ACCOUNTS } from "../../api";
import { navigate, PageTitle, Link, useLocation } from "../../app/router";
import { safeNext, useAuth } from "../../app/auth";
import { ErrorSummary, TextInput } from "../../components/Field";
import { Button, Card } from "../../components/ui";
import { AuthLayout } from "./AuthLayout";

export default function SignIn() {
  const { query } = useLocation();
  const { signIn } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [errors, setErrors] = useState<{ id: string; message: string }[]>([]);
  const [fail, setFail] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const summary = useRef<HTMLDivElement>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    const errs: { id: string; message: string }[] = [];
    if (!email.trim()) errs.push({ id: "email", message: "Enter your school email address" });
    if (!password) errs.push({ id: "password", message: "Enter your password" });
    setErrors(errs);
    setFail(null);
    if (errs.length) {
      queueMicrotask(() => summary.current?.focus());
      return;
    }
    setBusy(true);
    try {
      await signIn(email.trim(), password);
      navigate(safeNext(query.get("next")));
    } catch (ex) {
      setFail(ex instanceof ApiError ? ex.message : "We could not sign you in. Please try again.");
    } finally {
      setBusy(false);
    }
  }
  const err = (id: string) => errors.find((x) => x.id === id)?.message;

  return (
    <AuthLayout
      eyebrow="Welcome"
      title={<PageTitle title="Sign in">Sign in to Reading Helper</PageTitle>}
      intro={
        <p>
          Reading Helper is for K&ndash;3 teachers invited by their district. It gives
          research-based ideas. It never evaluates you or your students.
        </p>
      }
    >
      {query.get("signedout") && (
        <p role="status" className="rounded-xl bg-tint p-3 font-semibold">
          You have signed out.
        </p>
      )}
      <Card aria-labelledby="signin-form" className="rh-rise">
        <h2 id="signin-form" className="sr-only">
          Sign in form
        </h2>
        <form onSubmit={submit} noValidate className="flex flex-col gap-4">
          <ErrorSummary errors={errors} innerRef={summary} />
          {fail && (
            <p
              role="alert"
              className="rounded-xl border-2 border-idea bg-notice-bg p-3 font-semibold text-notice-text"
            >
              {fail}
            </p>
          )}
          <TextInput
            id="email"
            label="School email address"
            type="email"
            autoComplete="username"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            error={err("email")}
          />
          <div>
            <TextInput
              id="password"
              label="Password"
              type={show ? "text" : "password"}
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              error={err("password")}
            />
            <Button
              variant="quiet"
              aria-pressed={show}
              onClick={() => setShow(!show)}
              className="mt-1 !px-0"
            >
              {show ? "Hide password" : "Show password"}
            </Button>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <Button type="submit" variant="primary" disabled={busy}>
              {busy ? "Signing in…" : "Sign in"}
            </Button>
            <Link
              to="/forgot-password"
              className="inline-flex min-h-target items-center font-semibold text-primary underline"
            >
              Forgot your password?
            </Link>
          </div>
        </form>
      </Card>
      <Card aria-labelledby="no-account" tone="tint">
        <h2 id="no-account" className="font-heading text-lg font-semibold">
          Don&apos;t have an account?
        </h2>
        <p className="mt-1">
          Access is by invitation only. Request access and an administrator will review it.
        </p>
        <Link
          to="/request-access"
          className="mt-2 inline-flex min-h-target items-center font-semibold text-primary underline"
        >
          Request access
        </Link>
        <span className="mx-2" aria-hidden="true">
          ·
        </span>
        <Link
          to="/accept-invite"
          className="inline-flex min-h-target items-center font-semibold text-primary underline"
        >
          I have an invite code
        </Link>
      </Card>
      {IS_MOCK && (
        <Card aria-labelledby="examples" className="border-dashed">
          <h2 id="examples" className="font-heading text-base font-semibold">
            Example accounts (example mode only)
          </h2>
          <p className="mt-1 text-sm text-muted">
            These are fake accounts for trying the screens. They unlock nothing real.
          </p>
          <dl className="mt-2 grid gap-2 text-sm sm:grid-cols-2">
            {MOCK_ACCOUNTS.map((a) => (
              <div key={a.email} className="rounded-lg bg-bg p-2">
                <dt className="font-semibold">
                  {a.role === "admin" ? "Administrator" : "Teacher"}
                </dt>
                <dd>{a.email}</dd>
                <dd>{a.password}</dd>
              </div>
            ))}
          </dl>
        </Card>
      )}
    </AuthLayout>
  );
}
