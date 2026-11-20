import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Link } from "../app/router";
import { Icon } from "./Icon";

type Variant = "primary" | "secondary" | "quiet";
type Size = "normal" | "classroom";

const base =
  "inline-flex items-center justify-center gap-2 rounded-lg font-semibold text-center leading-tight transition-colors disabled:cursor-not-allowed disabled:opacity-60";
const sizes: Record<Size, string> = {
  normal: "min-h-target min-w-target px-5 py-2",
  classroom: "min-h-classroom min-w-classroom px-7 py-3 text-xl",
};
const variants: Record<Variant, string> = {
  primary: "bg-primary text-white hover:bg-primary-hover",
  secondary: "border border-control bg-surface text-ink hover:bg-bg",
  quiet: "text-primary underline hover:text-primary-hover",
};
export const buttonClass = (variant: Variant = "secondary", size: Size = "normal") =>
  `${base} ${sizes[size]} ${variants[variant]}`;

interface BtnProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  icon?: string;
}
export function Button({ variant, size, icon, className = "", children, ...rest }: BtnProps) {
  return (
    <button type="button" className={`${buttonClass(variant, size)} ${className}`} {...rest}>
      {icon && <Icon name={icon} />}
      {children}
    </button>
  );
}

export function LinkButton({
  to,
  query,
  variant,
  size,
  icon,
  className = "",
  children,
}: {
  to: string;
  query?: Record<string, string | undefined>;
  variant?: Variant;
  size?: Size;
  icon?: string;
  className?: string;
  children: ReactNode;
}) {
  return (
    <Link to={to} query={query} className={`${buttonClass(variant, size)} ${className}`}>
      {icon && <Icon name={icon} />}
      {children}
    </Link>
  );
}

/** A toggle that says its state in words and with a check mark, not only with color. */
export function ToggleChip({
  pressed,
  onClick,
  children,
  className = "",
}: {
  pressed: boolean;
  onClick: () => void;
  children: ReactNode;
  className?: string;
}) {
  return (
    <button
      type="button"
      aria-pressed={pressed}
      onClick={onClick}
      className={`inline-flex min-h-target min-w-target items-center justify-center gap-1 rounded-lg border-2 px-3 font-semibold ${
        pressed ? "border-primary bg-primary text-white" : "border-control bg-surface text-ink"
      } ${className}`}
    >
      {pressed && <Icon name="check" className="h-4 w-4" />}
      {children}
    </button>
  );
}

export function Card({
  children,
  className = "",
  as: Tag = "section",
  ...rest
}: {
  children: ReactNode;
  className?: string;
  as?: "section" | "div" | "article";
  "aria-labelledby"?: string;
}) {
  return (
    <Tag
      className={`rh-card rounded-2xl border border-border bg-surface p-5 ${className}`}
      {...rest}
    >
      {children}
    </Tag>
  );
}

export function Badge({
  children,
  tone = "primary",
}: {
  children: ReactNode;
  tone?: "primary" | "idea" | "plain";
}) {
  const t = {
    primary: "bg-primary text-white",
    idea: "bg-highlight text-ink",
    plain: "bg-bg text-ink border border-control",
  }[tone];
  return (
    <span className={`inline-block rounded-md px-3 py-1 text-sm font-bold ${t}`}>{children}</span>
  );
}

export function Breadcrumb({ items }: { items: { label: string; to?: string }[] }) {
  return (
    <nav aria-label="Breadcrumb" className="mb-3 text-sm">
      <ol className="flex flex-wrap items-center gap-x-2">
        {items.map((it, i) => (
          <li key={it.label} className="flex items-center gap-x-2">
            {i > 0 && <span aria-hidden="true">›</span>}
            {it.to ? (
              <Link to={it.to} className="text-primary underline">
                {it.label}
              </Link>
            ) : (
              <span aria-current="page" className="font-semibold">
                {it.label}
              </span>
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
}

/** Second-level navigation under the main nav (Tomorrow | Make a story | ...). */
export function SubNav({
  label,
  items,
  current,
}: {
  label: string;
  items: { label: string; to: string }[];
  current: string;
}) {
  return (
    <nav aria-label={label} className="mb-6 flex flex-wrap gap-2">
      {items.map((it) => (
        <Link
          key={it.to}
          to={it.to}
          aria-current={current === it.to ? "page" : undefined}
          className={`inline-flex min-h-target items-center rounded-lg px-4 font-semibold ${
            current === it.to
              ? "bg-primary text-white"
              : "border border-control bg-surface text-ink hover:bg-bg"
          }`}
        >
          {it.label}
        </Link>
      ))}
    </nav>
  );
}

export function ErrorMessage({ children, onRetry }: { children: ReactNode; onRetry?: () => void }) {
  return (
    <div
      role="alert"
      className="rh-card flex flex-wrap items-center gap-3 rounded-xl border-2 border-idea bg-notice-bg p-4 text-notice-text"
    >
      <Icon name="alert" className="h-6 w-6 shrink-0" />
      <p className="flex-1 font-semibold">{children}</p>
      {onRetry && (
        <Button onClick={onRetry} variant="secondary">
          Try again
        </Button>
      )}
    </div>
  );
}

export function ExampleChip() {
  return (
    <span className="inline-flex items-center gap-1 rounded-md border border-control bg-bg px-2 py-0.5 text-sm font-semibold">
      <Icon name="info" className="h-4 w-4" /> Example
    </span>
  );
}
