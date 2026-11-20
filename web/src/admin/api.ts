export const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export interface Source {
  source_id: string;
  title: string;
  authors: string[];
  year: number | null;
  doi: string | null;
  url: string | null;
  pdf_url: string | null;
  license: string | null;
  license_snapshot_url: string | null;
  status: "candidate" | "approved" | "rejected";
  publisher: string | null;
  jurisdiction: string | null;
  curation_status: string | null;
  curation_note: string | null;
  reviewer_notes: string | null;
}

export interface Checklist {
  copy_store: boolean;
  ai_use: boolean;
  excerpt_display: boolean;
  redistribution: boolean;
  derivatives: boolean;
  third_party_content_checked: boolean;
}

async function check(r: Response): Promise<Response> {
  if (r.ok) return r;
  let msg = `Request failed (${r.status})`;
  try {
    const body = await r.json();
    if (Array.isArray(body.detail)) msg = body.detail.join("; ");
    else if (typeof body.detail === "string") msg = body.detail;
  } catch {
    /* keep default message */
  }
  throw new Error(msg);
}

export async function listSources(status: Source["status"]): Promise<Source[]> {
  return (await check(await fetch(`${API_URL}/admin/sources?status=${status}`))).json();
}

export async function uploadSnapshot(id: string, file: File): Promise<void> {
  const form = new FormData();
  form.append("file", file);
  await check(
    await fetch(`${API_URL}/admin/sources/${id}/license-snapshot`, { method: "POST", body: form }),
  );
}

export async function decide(id: string, body: Record<string, unknown>): Promise<Source> {
  return (
    await check(
      await fetch(`${API_URL}/admin/sources/${id}/decision`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }),
    )
  ).json();
}

export interface AuditEntry {
  ts: string;
  actor: string;
  from_status: string | null;
  to_status: string;
  reason: string;
}

export async function reopen(id: string, reason: string): Promise<Source> {
  return (
    await check(
      await fetch(`${API_URL}/admin/sources/${id}/reopen`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason }),
      }),
    )
  ).json();
}

export async function getAudit(id: string): Promise<AuditEntry[]> {
  return (await check(await fetch(`${API_URL}/admin/sources/${id}/audit`))).json();
}
