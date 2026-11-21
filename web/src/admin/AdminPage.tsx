import { useState } from "react";
import { PageTitle } from "../app/router";
import AccessRequests from "./AccessRequests";
import AdminReview from "./AdminReview";

export default function AdminPage() {
  const [tab, setTab] = useState<"sources" | "access">("sources");
  return (
    <>
      <PageTitle title="Admin">Admin</PageTitle>
      <div role="tablist" aria-label="Admin sections" className="mt-4 flex flex-wrap gap-2">
        {(
          [
            ["sources", "Source queue"],
            ["access", "Access requests"],
          ] as const
        ).map(([k, label]) => (
          <button
            key={k}
            role="tab"
            type="button"
            id={`tab-${k}`}
            aria-selected={tab === k}
            aria-controls={`panel-${k}`}
            tabIndex={tab === k ? 0 : -1}
            onClick={() => setTab(k)}
            onKeyDown={(e) => {
              if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
                const n = tab === "sources" ? "access" : "sources";
                setTab(n);
                document.getElementById(`tab-${n}`)?.focus();
              }
            }}
            className={`min-h-target rounded-full px-5 font-semibold ${tab === k ? "bg-primary text-white" : "border border-control bg-surface"}`}
          >
            {label}
          </button>
        ))}
      </div>
      <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`} className="mt-6">
        {tab === "sources" ? <AdminReview /> : <AccessRequests />}
      </div>
    </>
  );
}
