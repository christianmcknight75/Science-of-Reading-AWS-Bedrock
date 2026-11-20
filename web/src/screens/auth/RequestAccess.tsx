import { useRef, useState, type FormEvent } from "react";
import { ApiError, requestAccess } from "../../api";
import { navigate, PageTitle, Link } from "../../app/router";
import { ErrorSummary, Field, TextInput, describedBy, inputClass } from "../../components/Field";
import { Button, Card } from "../../components/ui";
import { AuthLayout } from "./AuthLayout";

const ROLES = [
  "Classroom teacher",
  "Reading coach or interventionist",
  "School leader",
  "District staff",
  "Other",
];

export default function RequestAccess() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [district, setDistrict] = useState("");
  const [role, setRole] = useState("");
  const [errors, setErrors] = useState<{ id: string; message: string }[]>([]);
  const [fail, setFail] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const summary = useRef<HTMLDivElement>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    const errs: { id: string; message: string }[] = [];
    if (!name.trim()) errs.push({ id: "name", message: "Enter your name" });
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim()))
      errs.push({ id: "email", message: "Enter a school email address, like name@school.org" });
    if (!district.trim()) errs.push({ id: "district", message: "Enter your district or school" });
    if (!role) errs.push({ id: "role", message: "Choose your role" });
    setErrors(errs);
    setFail(null);
    if (errs.length) {
      queueMicrotask(() => summary.current?.focus());
      return;
    }
    setBusy(true);
    try {
      // The contract has {name, email, district}. Role rides along in the district text until the
      // contract adds a field (see the open question in the summary).
      await requestAccess({
        name: name.trim(),
        email: email.trim(),
        district: `${district.trim()} (${role})`,
      });
      navigate("/request-received");
    } catch (ex) {
      setFail(
        ex instanceof ApiError ? ex.message : "We could not send your request. Please try again.",
      );
    } finally {
      setBusy(false);
    }
  }
  const err = (id: string) => errors.find((x) => x.id === id)?.message;

  return (
    <AuthLayout
      eyebrow="Closed access"
      title={<PageTitle title="Request access">Request access</PageTitle>}
      intro={
        <p>
          Reading Helper is invite-only. Tell us who you are and an administrator will review your
          request. There is no public sign-up.
        </p>
      }
    >
      <Card aria-labelledby="req-form" className="rh-rise">
        <h2 id="req-form" className="sr-only">
          Request access form
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
            id="name"
            label="Your name"
            autoComplete="name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            error={err("name")}
          />
          <TextInput
            id="email"
            label="School email address"
            hint="Use your school or district address."
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            error={err("email")}
          />
          <TextInput
            id="district"
            label="District or school"
            autoComplete="organization"
            value={district}
            onChange={(e) => setDistrict(e.target.value)}
            error={err("district")}
          />
          <Field id="role" label="Your role" error={err("role")}>
            <select
              id="role"
              value={role}
              onChange={(e) => setRole(e.target.value)}
              aria-invalid={err("role") ? true : undefined}
              aria-describedby={describedBy("role", undefined, err("role"))}
              className={inputClass(err("role"))}
            >
              <option value="">Choose one</option>
              {ROLES.map((r) => (
                <option key={r}>{r}</option>
              ))}
            </select>
          </Field>
          <p className="text-sm text-muted">
            We only ask for what we need to review your request. Please don&apos;t include any
            student information.
          </p>
          <div className="flex flex-wrap items-center gap-3">
            <Button type="submit" variant="primary" disabled={busy}>
              {busy ? "Sending…" : "Send request"}
            </Button>
            <Link
              to="/signin"
              className="inline-flex min-h-target items-center font-semibold text-primary underline"
            >
              Back to sign in
            </Link>
          </div>
        </form>
      </Card>
    </AuthLayout>
  );
}
