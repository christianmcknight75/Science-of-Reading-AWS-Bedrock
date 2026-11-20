import { useCallback, useEffect, useState } from "react";
import {
  decide,
  getAudit,
  listSources,
  reopen,
  uploadSnapshot,
  type AuditEntry,
  type Source,
} from "./api";

const USES = [
  ["copy_store", "We may copy and store the full text"],
  ["ai_use", "AI may process the text"],
  ["excerpt_display", "We may show exact passages to teachers"],
  ["redistribution", "We may redistribute it (recorded only)"],
  ["derivatives", "We may make derivative works such as summaries (recorded only)"],
  ["third_party_content_checked", "I checked figures and tables for separate copyright"],
] as const;

const btn =
  "min-h-target min-w-target rounded-lg px-5 py-2 font-semibold focus-visible:outline focus-visible:outline-4 focus-visible:outline-offset-2 focus-visible:outline-primary";

function ReviewForm({ source, onDone }: { source: Source; onDone: () => void }) {
  const [uses, setUses] = useState<Record<string, boolean>>({});
  const [license, setLicense] = useState(source.license ?? "");
  const [attribution, setAttribution] = useState("");
  const [notes, setNotes] = useState("");
  const [randomized, setRandomized] = useState(false);
  const [comparison, setComparison] = useState(false);
  const [sampleSize, setSampleSize] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [errors, setErrors] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);

  async function submit(decision: "approve" | "reject") {
    setBusy(true);
    setErrors([]);
    try {
      if (decision === "approve" && file) await uploadSnapshot(source.source_id, file);
      await decide(source.source_id, {
        decision,
        reviewer_notes: notes,
        randomized: decision === "approve" ? randomized : null,
        has_comparison_group: decision === "approve" ? comparison : null,
        sample_size: sampleSize ? Number(sampleSize) : null,
        license: license || null,
        attribution: attribution || null,
        checklist:
          decision === "approve"
            ? { ...Object.fromEntries(USES.map(([k]) => [k, false])), ...uses }
            : null,
      });
      onDone();
    } catch (e) {
      setErrors([(e as Error).message]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={(e) => e.preventDefault()} className="space-y-6">
      <h2 className="text-xl font-semibold">{source.title}</h2>
      <section aria-labelledby="s1">
        <h3 id="s1" className="font-heading font-semibold">
          1. Identify the source
        </h3>
        <dl className="mt-2">
          <dt className="font-semibold">Publisher</dt>
          <dd>{source.publisher ?? "unknown"}</dd>
          <dt className="font-semibold">Jurisdiction</dt>
          <dd>{source.jurisdiction ?? "unknown"}</dd>
          <dt className="font-semibold">Year</dt>
          <dd>{source.year ?? "unknown"}</dd>
          <dt className="font-semibold">DOI</dt>
          <dd>{source.doi ?? "none"}</dd>
          <dt className="font-semibold">Link</dt>
          <dd>
            {source.url ? (
              <a className="text-primary underline" href={source.url}>
                Open the paper
              </a>
            ) : (
              "none"
            )}
          </dd>
        </dl>
      </section>
      {source.curation_note && (
        <p className="rounded-lg bg-notice-bg p-3 text-notice-text">
          <strong>Curator note:</strong> {source.curation_note}
        </p>
      )}
      <div>
        <label htmlFor="license" className="block font-semibold">
          2. License (for example cc-by)
        </label>
        <input
          id="license"
          value={license}
          onChange={(e) => setLicense(e.target.value)}
          className="min-h-target w-full rounded-lg border border-border px-3"
        />
      </div>
      <fieldset className="space-y-2">
        <legend className="font-heading font-semibold">
          3. Allowed uses and third-party content
        </legend>
        {USES.map(([key, label]) => (
          <label key={key} className="flex min-h-target items-center gap-3">
            <input
              type="checkbox"
              className="h-6 w-6"
              checked={!!uses[key]}
              onChange={(e) => setUses({ ...uses, [key]: e.target.checked })}
            />
            {label}
          </label>
        ))}
      </fieldset>
      <div>
        <label htmlFor="attr" className="block font-semibold">
          4. Attribution text
        </label>
        <input
          id="attr"
          value={attribution}
          onChange={(e) => setAttribution(e.target.value)}
          className="min-h-target w-full rounded-lg border border-border px-3"
        />
      </div>
      <div>
        <label htmlFor="snap" className="block font-semibold">
          5. License snapshot (PDF, HTML, PNG or TXT)
        </label>
        <input
          id="snap"
          type="file"
          accept=".pdf,.html,.htm,.png,.txt"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="min-h-target"
        />
        {source.license_snapshot_url && <p>A snapshot is already on file.</p>}
      </div>
      <fieldset className="space-y-2">
        <legend className="font-heading font-semibold">
          6. Study design (only for single studies; used for the evidence label)
        </legend>
        <label className="flex min-h-target items-center gap-3">
          <input
            type="checkbox"
            className="h-6 w-6"
            checked={randomized}
            onChange={(e) => setRandomized(e.target.checked)}
          />
          Randomized
        </label>
        <label className="flex min-h-target items-center gap-3">
          <input
            type="checkbox"
            className="h-6 w-6"
            checked={comparison}
            onChange={(e) => setComparison(e.target.checked)}
          />
          Has a comparison group
        </label>
        <div>
          <label htmlFor="n" className="block">
            Number of students
          </label>
          <input
            id="n"
            type="number"
            min={1}
            value={sampleSize}
            onChange={(e) => setSampleSize(e.target.value)}
            className="min-h-target rounded-lg border border-border px-3"
          />
        </div>
      </fieldset>
      <div>
        <label htmlFor="notes" className="block font-semibold">
          Reviewer notes
        </label>
        <textarea
          id="notes"
          rows={3}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          className="w-full rounded-lg border border-border p-3"
        />
      </div>
      {errors.length > 0 && (
        <div role="alert" className="rounded-lg bg-notice-bg p-4 text-notice-text">
          <strong>Cannot save yet:</strong> {errors.join(" ")}
        </div>
      )}
      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          disabled={busy}
          onClick={() => submit("approve")}
          className={`${btn} bg-primary text-white hover:bg-primary-hover`}
        >
          Approve source
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => submit("reject")}
          className={`${btn} border border-primary text-primary`}
        >
          Reject source
        </button>
      </div>
    </form>
  );
}

function ReopenPanel({ source, onDone }: { source: Source; onDone: () => void }) {
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [log, setLog] = useState<AuditEntry[]>([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getAudit(source.source_id)
      .then(setLog)
      .catch(() => setLog([]));
  }, [source.source_id]);

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      await reopen(source.source_id, reason);
      onDone();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold">{source.title}</h2>
      <p>
        Status: <strong>{source.status}</strong>
        {source.curation_status && source.curation_status !== "ready" && (
          <>
            {" "}
            · Curation: <strong>{source.curation_status}</strong>
          </>
        )}
      </p>
      {source.curation_note && (
        <p className="rounded-lg bg-notice-bg p-3 text-notice-text">
          <strong>Curator note:</strong> {source.curation_note}
        </p>
      )}
      <form onSubmit={(e) => e.preventDefault()} className="space-y-3">
        <label htmlFor="reason" className="block font-semibold">
          Reason for re-opening (required, saved with your name and the time)
        </label>
        <textarea
          id="reason"
          rows={3}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          className="w-full rounded-lg border border-border p-3"
        />
        {error && (
          <div role="alert" className="rounded-lg bg-notice-bg p-4 text-notice-text">
            <strong>Cannot re-open yet:</strong> {error}
          </div>
        )}
        <button
          type="button"
          disabled={busy || reason.trim().length < 5}
          onClick={submit}
          className={`${btn} bg-primary text-white hover:bg-primary-hover disabled:opacity-60`}
        >
          Re-open as candidate
        </button>
      </form>
      <section aria-labelledby="hist">
        <h3 id="hist" className="font-heading font-semibold">
          History
        </h3>
        {log.length === 0 ? (
          <p>No logged changes yet.</p>
        ) : (
          <ul className="space-y-2">
            {log.map((e, i) => (
              <li key={i} className="rounded-lg border border-border bg-surface p-3">
                {new Date(e.ts).toLocaleString()} · {e.actor}: {e.from_status ?? "new"} to{" "}
                {e.to_status}. {e.reason}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

export default function AdminReview() {
  const [sources, setSources] = useState<Source[] | null>(null);
  const [selected, setSelected] = useState<Source | null>(null);
  const [tab, setTab] = useState<Source["status"]>("candidate");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    listSources(tab)
      .then(setSources)
      .catch((e: Error) => setError(e.message));
  }, [tab]);
  useEffect(() => {
    load();
  }, [load]);
  const done = () => {
    setSelected(null);
    load();
  };

  return (
    <main className="mx-auto max-w-5xl p-6">
      <h1 className="text-2xl font-semibold">Source review queue</h1>
      <p className="text-muted">
        Only approved sources with a completed license record enter the research library.
      </p>
      {error && (
        <p role="alert" className="mt-4 rounded-lg bg-notice-bg p-4 text-notice-text">
          {error}
        </p>
      )}
      {sources === null && !error && <p role="status">Loading sources…</p>}
      {sources?.length === 0 && (
        <p role="status" className="mt-4">
          No sources in this list.
        </p>
      )}
      <div role="group" aria-label="Show sources that are" className="mt-4 flex flex-wrap gap-2">
        {(["candidate", "approved", "rejected"] as const).map((t) => (
          <button
            key={t}
            type="button"
            aria-pressed={tab === t}
            onClick={() => {
              setSources(null);
              setSelected(null);
              setTab(t);
            }}
            className={`${btn} border border-primary aria-pressed:bg-primary aria-pressed:text-white`}
          >
            {t === "candidate" ? "Waiting for review" : t === "approved" ? "Approved" : "Rejected"}
          </button>
        ))}
      </div>
      <div className="mt-6 grid gap-8 md:grid-cols-[1fr_2fr]">
        <nav aria-label="Candidate sources">
          <ul className="space-y-2">
            {sources?.map((s) => (
              <li key={s.source_id}>
                <button
                  type="button"
                  onClick={() => setSelected(s)}
                  aria-current={selected?.source_id === s.source_id ? "true" : undefined}
                  className="min-h-target w-full rounded-lg border border-border bg-surface px-3 py-2 text-left aria-[current=true]:border-4 aria-[current=true]:border-primary"
                >
                  {s.title}{" "}
                  <span className="text-muted">
                    ({s.year ?? "n.d."}, status: {s.status})
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </nav>
        <div>
          {selected && selected.status === "candidate" ? (
            <ReviewForm key={selected.source_id} source={selected} onDone={done} />
          ) : selected ? (
            <ReopenPanel key={selected.source_id} source={selected} onDone={done} />
          ) : sources?.length ? (
            <p>Pick a source to review.</p>
          ) : null}
        </div>
      </div>
    </main>
  );
}
