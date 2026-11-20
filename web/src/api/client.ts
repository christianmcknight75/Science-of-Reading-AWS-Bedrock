// Real API client. One function per backend call, typed with ./types.
import { clearToken, getToken, setToken } from "./session";
import {
  ApiError,
  type AccessRequest,
  type ApproveResult,
  type Me,
  type RequestAccessBody,
  type RequestStatus,
  type Role,
  type SignInResult,
  type AskRequest,
  type AskResult,
  type DecodableCheckRequest,
  type Feedback,
  type WordCheck,
  type GroupPlan,
  type MistakePair,
  type MistakeResult,
  type Refresher,
  type Skill,
  type Story,
  type StoryRequest,
  type TrainingPlan,
  type TrainingTopic,
} from "./types";

export const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function request<T>(method: "GET" | "POST", path: string, body?: unknown): Promise<T> {
  let r: Response;
  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`; // contract: bearer on everything but sign-in etc.
  try {
    r = await fetch(`${API_URL}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(
      "We could not reach Reading Helper. Check your connection and try again.",
      0,
    );
  }
  if (!r.ok) {
    let msg = `Something went wrong (${r.status}).`;
    try {
      const j = await r.json();
      if (typeof j.detail === "string") msg = j.detail;
    } catch {
      /* keep the default message */
    }
    if (r.status === 401 && token) {
      clearToken(); // expired or revoked: the app returns to the sign-in screen
      window.dispatchEvent(new Event("rh-signed-out"));
    }
    if (r.status === 404) msg = "This part of Reading Helper is not ready yet.";
    throw new ApiError(msg, r.status);
  }
  if (r.status === 204) return undefined as T;
  return (await r.json()) as T;
}

// Built: api/app/qa.py. 503 = kill switch, 429 = rate limit (message is teacher-ready).
export const ask = (req: AskRequest) => request<AskResult>("POST", "/api/ask", req);

// Phase 4 (built behind the fake model client: docs/API_CONTRACT.md)
export const getGroupPlan = (focus: Skill, sounds: string[]) =>
  request<GroupPlan>("POST", "/api/group-plan", { focus, sounds });
export const makeStory = (req: StoryRequest) => request<Story>("POST", "/api/story", req);
export const diagnoseMistakes = (pairs: MistakePair[]) =>
  request<MistakeResult>("POST", "/api/stuck", { pairs });
export const listTrainingTopics = () => request<TrainingTopic[]>("GET", "/api/training/topics");
export const getTrainingPlan = (topicId: string) =>
  request<TrainingPlan>("GET", `/api/training/topics/${encodeURIComponent(topicId)}`);
/** Plain-code word check (no model): used whenever a teacher changes the sounds. */
export const checkDecodable = (req: DecodableCheckRequest) =>
  request<{ checks: WordCheck[] }>("POST", "/api/decodable/check", req).then((r) => r.checks);
export const getRefresher = () => request<Refresher>("GET", "/api/refresher/today");
export const sendFeedback = (fb: Feedback) => request<void>("POST", "/api/feedback", fb);

// Accounts (contract: docs/API_CONTRACT.md). Public: sign-in, request-access, accept-invite.
const keep = async (p: Promise<SignInResult>) => {
  const r = await p;
  setToken(r.access_token);
  return r;
};
export const signIn = (email: string, password: string) =>
  keep(request<SignInResult>("POST", "/api/auth/sign-in", { email, password }));
export const signOutApi = async () => {
  try {
    await request<void>("POST", "/api/auth/sign-out");
  } finally {
    clearToken();
  }
};
export const getMe = () => request<Me>("GET", "/api/auth/me");
export const acceptInvite = (email: string, invite_code: string, password: string) =>
  keep(request<SignInResult>("POST", "/api/auth/accept-invite", { email, invite_code, password }));
export const requestAccess = (b: RequestAccessBody) =>
  request<{ message: string }>("POST", "/api/auth/request-access", b);
export const listAccessRequests = (status: RequestStatus) =>
  request<AccessRequest[]>("GET", `/api/admin/access-requests?status=${status}`);
export const approveAccessRequest = (id: AccessRequest["request_id"], role: Role = "teacher") =>
  request<ApproveResult>("POST", `/api/admin/access-requests/${id}/approve`, { role });
export const denyAccessRequest = (id: AccessRequest["request_id"], reason: string) =>
  request<void>("POST", `/api/admin/access-requests/${id}/deny`, { reason });
