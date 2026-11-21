import type { InputHTMLAttributes, ReactNode } from "react";

/** Label above the field, optional hint, and an error that is tied to the field for screen readers. */
export function Field({
  id,
  label,
  hint,
  error,
  children,
}: {
  id: string;
  label: string;
  hint?: string;
  error?: string;
  children: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="font-semibold">
        {label}
      </label>
      {hint && (
        <p id={`${id}-hint`} className="text-sm text-muted">
          {hint}
        </p>
      )}
      {error && (
        <p id={`${id}-error`} className="font-semibold text-notice-text">
          <span className="mr-1 rounded bg-notice-bg px-1">Error:</span>
          {error}
        </p>
      )}
      {children}
    </div>
  );
}

export const inputClass = (error?: string) =>
  `min-h-target w-full rounded-lg border bg-surface px-3 ${error ? "border-2 border-idea" : "border-control"}`;

export function describedBy(id: string, hint?: string, error?: string) {
  return (
    [hint ? `${id}-hint` : "", error ? `${id}-error` : ""].filter(Boolean).join(" ") || undefined
  );
}

export function TextInput({
  id,
  label,
  hint,
  error,
  ...rest
}: {
  id: string;
  label: string;
  hint?: string;
  error?: string;
} & InputHTMLAttributes<HTMLInputElement>) {
  return (
    <Field id={id} label={label} hint={hint} error={error}>
      <input
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy(id, hint, error)}
        className={inputClass(error)}
        {...rest}
      />
    </Field>
  );
}

/** Error summary at the top of a form: focus moves here on a failed submit; each item links to its field. */
export function ErrorSummary({
  errors,
  innerRef,
}: {
  errors: { id: string; message: string }[];
  innerRef: React.RefObject<HTMLDivElement | null>;
}) {
  if (errors.length === 0) return null;
  return (
    <div
      ref={innerRef}
      tabIndex={-1}
      role="alert"
      className="rounded-xl border-2 border-idea bg-notice-bg p-4 text-notice-text"
    >
      <h2 className="font-heading text-lg font-semibold">There is a problem</h2>
      <ul className="mt-2 list-disc pl-5">
        {errors.map((e) => (
          <li key={e.id}>
            <a
              href={`#${e.id}`}
              className="inline-flex min-h-target items-center font-semibold underline"
              onClick={(ev) => {
                ev.preventDefault();
                document.getElementById(e.id)?.focus();
              }}
            >
              {e.message}
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}
