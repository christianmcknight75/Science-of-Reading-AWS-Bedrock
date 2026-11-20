import { useCallback, useEffect, useState } from "react";
import {
  ApiError,
  approveAccessRequest,
  denyAccessRequest,
  IS_MOCK,
  listAccessRequests,
  type AccessRequest,
  type RequestStatus,
} from "../api";
import { Button, Card } from "../components/ui";

const TABS: [RequestStatus, string][] = [
  ["pending", "Waiting for review"],
  ["approved", "Approved"],
  ["denied", "Denied"],
];
const when = (iso: string) =>
  new Date(iso).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });

export default function AccessRequests() {
  const [status, setStatus] = useState<RequestStatus>("pending");
  const [rows, setRows] = useState<AccessRequest[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [denying, setDenying] = useState<AccessRequest["request_id"] | null>(null);
  const [reason, setReason] = useState("");

  const load = useCallback(() => {
    listAccessRequests(status).then(setRows, (e: unknown) =>
      setError(e instanceof ApiError ? e.message : "Something went wrong."),
    );
  }, [status]);
  useEffect(load, [load]);

  async function approve(r: AccessRequest) {
    setError(null);
    try {
      const res = await approveAccessRequest(r.request_id, "teacher");
      setNote(
        `Approved ${r.name}. Invite code: ${res.invite_code}. This is shown once. ${IS_MOCK ? "(Example mode: no email is sent.) " : ""}Give it to them securely.`,
      );
      load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Something went wrong.");
    }
  }
  async function deny(r: AccessRequest) {
    setError(null);
    if (!reason.trim()) {
      setError("Please give a short reason for denying this request.");
      return;
    }
    try {
      await denyAccessRequest(r.request_id, reason.trim());
      setNote(`Denied ${r.name}.`);
      setDenying(null);
      setReason("");
      load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Something went wrong.");
    }
  }

  return (
    <section aria-labelledby="access-h">
      <h2 id="access-h" className="font-heading text-2xl font-semibold">
        Access requests
      </h2>
      <p className="mt-1 text-muted">
        Reading Helper is invite-only. Approving a request creates the account and gives you a
        one-time invite code. Every decision is recorded.
      </p>
      <div role="group" aria-label="Show requests that are" className="mt-4 flex flex-wrap gap-2">
        {TABS.map(([k, label]) => (
          <Button
            key={k}
            aria-pressed={status === k}
            variant={status === k ? "primary" : "secondary"}
            onClick={() => {
              setRows(null);
              setStatus(k);
              setNote(null);
              setError(null);
              setDenying(null);
            }}
          >
            {label}
          </Button>
        ))}
      </div>
      {error && (
        <p
          role="alert"
          className="mt-4 rounded-xl border-2 border-idea bg-notice-bg p-3 font-semibold text-notice-text"
        >
          {error}
        </p>
      )}
      <p role="status" className={note ? "mt-4 rounded-xl bg-tint p-3 font-semibold" : "sr-only"}>
        {note}
      </p>
      {rows === null && !error && (
        <p role="status" className="mt-4">
          Loading requests…
        </p>
      )}
      {rows?.length === 0 && <p className="mt-4">No requests in this list.</p>}
      <ul className="mt-4 flex flex-col gap-3">
        {rows?.map((r) => (
          <li key={r.request_id}>
            <Card as="article" aria-labelledby={`r-${r.request_id}`}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 id={`r-${r.request_id}`} className="font-heading text-lg font-semibold">
                    {r.name}
                  </h3>
                  <p>{r.email}</p>
                  <p className="text-muted">{r.district}</p>
                  <p className="text-sm text-muted">
                    Requested {when(r.requested_at)}
                    {r.decided_at ? ` · decided ${when(r.decided_at)}` : ""}
                    {r.decision_reason ? ` · reason: ${r.decision_reason}` : ""}
                  </p>
                </div>
                {r.status === "pending" && denying !== r.request_id && (
                  <div className="flex flex-wrap gap-2">
                    <Button
                      variant="primary"
                      onClick={() => approve(r)}
                      aria-label={`Approve ${r.name}`}
                    >
                      Approve
                    </Button>
                    <Button onClick={() => setDenying(r.request_id)} aria-label={`Deny ${r.name}`}>
                      Deny
                    </Button>
                  </div>
                )}
              </div>
              {denying === r.request_id && (
                <form
                  className="mt-3 flex flex-col gap-2"
                  onSubmit={(e) => {
                    e.preventDefault();
                    void deny(r);
                  }}
                >
                  <label htmlFor={`why-${r.request_id}`} className="font-semibold">
                    Reason for denying (required)
                  </label>
                  <input
                    id={`why-${r.request_id}`}
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    className="min-h-target rounded-lg border border-control bg-surface px-3"
                  />
                  <div className="flex gap-2">
                    <Button type="submit" variant="primary">
                      Confirm deny
                    </Button>
                    <Button onClick={() => setDenying(null)}>Cancel</Button>
                  </div>
                </form>
              )}
            </Card>
          </li>
        ))}
      </ul>
    </section>
  );
}
