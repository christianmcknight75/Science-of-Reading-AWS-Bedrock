import type { ReactNode } from "react";
import { Mascot, type MascotState } from "../../components/Mascot";
import { Card } from "../../components/ui";

/** Two-column public layout: a warm welcome on the left, the form on the right. */
export function AuthLayout({
  mascot = "idle",
  eyebrow,
  title,
  intro,
  children,
}: {
  mascot?: MascotState;
  eyebrow: string;
  title: ReactNode;
  intro: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="mx-auto grid max-w-5xl items-start gap-6 py-4 md:grid-cols-[minmax(0,5fr)_minmax(0,6fr)] md:py-10">
      <Card tone="warm" aria-labelledby="auth-welcome" className="rh-rise !p-6 sm:!p-8">
        <Mascot state={mascot} size={120} />
        <p className="eyebrow mt-3">{eyebrow}</p>
        <div id="auth-welcome">{title}</div>
        <div className="mt-3 text-lg text-muted">{intro}</div>
      </Card>
      <div className="flex flex-col gap-5">{children}</div>
    </div>
  );
}
