import { clearToken, getToken } from "../api/session";

export const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

/** The admin calls need the same bearer token as every other call (docs/API_CONTRACT.md). */
function authed(init: RequestInit = {}): RequestInit {
  const token = getToken();
  return token
    ? {
        ...init,
        headers: { ...(init.headers as Record<string, string>), Authorization: `Bearer ${token}` },
      }
    : init;
}

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
  attribution: string | null;
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
  if (r.status === 401) {
    clearToken(); // expired or signed out: the app returns to the sign-in screen
    window.dispatchEvent(new Event("rh-signed-out"));
  }
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
  return (await check(await fetch(`${API_URL}/admin/sources?status=${status}`, authed()))).json();
}

export async function uploadSnapshot(id: string, file: File): Promise<void> {
  const form = new FormData();
  form.append("file", file);
  await check(
    await fetch(
      `${API_URL}/admin/sources/${id}/license-snapshot`,
      authed({ method: "POST", body: form }),
    ),
  );
}

export async function decide(id: string, body: Record<string, unknown>): Promise<Source> {
  return (
    await check(
      await fetch(
        `${API_URL}/admin/sources/${id}/decision`,
        authed({
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        }),
      ),
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
      await fetch(
        `${API_URL}/admin/sources/${id}/reopen`,
        authed({
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ reason }),
        }),
      ),
    )
  ).json();
}

export async function getAudit(id: string): Promise<AuditEntry[]> {
  return (await check(await fetch(`${API_URL}/admin/sources/${id}/audit`, authed()))).json();
}
