import { useRef, useState, type FormEvent } from "react";
import { ApiError, IS_MOCK, acceptInvite } from "../../api";
import { Link, navigate, PageTitle } from "../../app/router";
import { useAuth } from "../../app/auth";
import { ErrorSummary, TextInput } from "../../components/Field";
import { Button, Card } from "../../components/ui";
import { AuthLayout } from "./AuthLayout";

const linkCls = "inline-flex min-h-target items-center font-semibold text-primary underline";

export function RequestReceived() {
  return (
    <AuthLayout
      eyebrow="Request received"
      title={<PageTitle title="Request received">We&apos;ve got your request</PageTitle>}
      intro={
        <p>
          An administrator will review it. We&apos;ll email you at the address you gave if it is
          approved.
        </p>
      }
    >
      <Card aria-labelledby="what-next" className="rh-rise">
        <h2 id="what-next" className="font-heading text-lg font-semibold">
          What happens next
        </h2>
        <ol className="mt-2 list-decimal pl-6">
          <li>An administrator reviews your request.</li>
          <li>If approved, you get an invite code by email.</li>
          <li>You use the code to choose a password and sign in.</li>
        </ol>
        <Link to="/signin" className={`${linkCls} mt-3`}>
          Back to sign in
        </Link>
      </Card>
    </AuthLayout>
  );
}

export function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [errors, setErrors] = useState<{ id: string; message: string }[]>([]);
  const summary = useRef<HTMLDivElement>(null);
  function submit(e: FormEvent) {
    e.preventDefault();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      setErrors([{ id: "email", message: "Enter your school email address" }]);
      queueMicrotask(() => summary.current?.focus());
      return;
    }
    navigate("/forgot-sent");
  }
  return (
    <AuthLayout
      mascot="pointing"
      eyebrow="Password help"
      title={<PageTitle title="Forgot password">Forgot your password?</PageTitle>}
      intro={<p>Enter your school email address and we&apos;ll tell you how to get back in.</p>}
    >
      <Card aria-labelledby="forgot-form" className="rh-rise">
        <h2 id="forgot-form" className="sr-only">
          Password help form
        </h2>
        <form onSubmit={submit} noValidate className="flex flex-col gap-4">
          <ErrorSummary errors={errors} innerRef={summary} />
          <TextInput
            id="email"
            label="School email address"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            error={errors[0]?.message}
          />
          <div className="flex flex-wrap items-center gap-3">
            <Button type="submit" variant="primary">
              Continue
            </Button>
            <Link to="/signin" className={linkCls}>
              Back to sign in
            </Link>
          </div>
        </form>
      </Card>
    </AuthLayout>
  );
}

export function ForgotSent() {
  return (
    <AuthLayout
      eyebrow="Check your email"
      title={<PageTitle title="Check your email">Check your email</PageTitle>}
      intro={
        <p>
          If there is an account for that address, we&apos;ve sent instructions for choosing a new
          password. We say this either way, so nobody can use this page to find out who has an
          account.
        </p>
      }
    >
      <Card aria-labelledby="forgot-next" className="rh-rise">
        <h2 id="forgot-next" className="font-heading text-lg font-semibold">
          Nothing arrived?
        </h2>
        <p className="mt-1">
          Check your spam folder, or ask your administrator for a new invite code.{" "}
          {IS_MOCK
            ? "(Example mode: no email is sent.)"
            : "(Password reset by email is not switched on yet: your administrator can help.)"}
        </p>
        <Link to="/signin" className={`${linkCls} mt-2`}>
          Back to sign in
        </Link>
      </Card>
    </AuthLayout>
  );
}

export function AcceptInvite() {
  const { adopt } = useAuth();
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [pw, setPw] = useState("");
  const [errors, setErrors] = useState<{ id: string; message: string }[]>([]);
  const [fail, setFail] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const summary = useRef<HTMLDivElement>(null);
  async function submit(e: FormEvent) {
    e.preventDefault();
    const errs: { id: string; message: string }[] = [];
    if (!email.trim()) errs.push({ id: "email", message: "Enter your school email address" });
    if (!code.trim()) errs.push({ id: "code", message: "Enter your invite code" });
    if (pw.length < 12)
      errs.push({ id: "pw", message: "Choose a password with at least 12 characters" });
    setErrors(errs);
    setFail(null);
    if (errs.length) {
      queueMicrotask(() => summary.current?.focus());
      return;
    }
    setBusy(true);
    try {
      const r = await acceptInvite(email.trim(), code.trim(), pw);
      adopt(r.user);
      navigate("/");
    } catch (ex) {
      setFail(ex instanceof ApiError ? ex.message : "That did not work. Please try again.");
    } finally {
      setBusy(false);
    }
  }
  const err = (id: string) => errors.find((x) => x.id === id)?.message;
  return (
    <AuthLayout
      eyebrow="You're invited"
      title={<PageTitle title="Set your password">Set your password</PageTitle>}
      intro={<p>Enter the invite code from your email and choose a password.</p>}
    >
      <Card aria-labelledby="invite-form" className="rh-rise">
        <h2 id="invite-form" className="sr-only">
          Invite form
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
          <TextInput
            id="code"
            label="Invite code"
            autoComplete="one-time-code"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            error={err("code")}
          />
          <TextInput
            id="pw"
            label="New password"
            hint="At least 12 characters."
            type="password"
            autoComplete="new-password"
            value={pw}
            onChange={(e) => setPw(e.target.value)}
            error={err("pw")}
          />
          <div className="flex flex-wrap items-center gap-3">
            <Button type="submit" variant="primary" disabled={busy}>
              {busy ? "Saving…" : "Set password and sign in"}
            </Button>
            <Link to="/signin" className={linkCls}>
              Back to sign in
            </Link>
          </div>
        </form>
      </Card>
    </AuthLayout>
  );
}
