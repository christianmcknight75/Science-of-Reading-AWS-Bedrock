// Real API client. One function per backend call, typed with ./types.
// Only /api/ask exists on the server today; the others are the proposed Phase 4 contract.
import {
  ApiError,
  type AskRequest,
  type AskResult,
  type Feedback,
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
  try {
    r = await fetch(`${API_URL}${path}`, {
      method,
      headers: body === undefined ? undefined : { "Content-Type": "application/json" },
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
    if (r.status === 404) msg = "This part of Reading Helper is not ready yet.";
    throw new ApiError(msg, r.status);
  }
  return (await r.json()) as T;
}

// Built: api/app/qa.py. 503 = kill switch, 429 = rate limit (message is teacher-ready).
export const ask = (req: AskRequest) => request<AskResult>("POST", "/api/ask", req);

// PROPOSED (not built yet)
export const getGroupPlan = (focus: Skill, sounds: string[]) =>
  request<GroupPlan>("POST", "/api/group-plan", { focus, sounds });
export const makeStory = (req: StoryRequest) => request<Story>("POST", "/api/story", req);
export const diagnoseMistakes = (pairs: MistakePair[]) =>
  request<MistakeResult>("POST", "/api/stuck", { pairs });
export const listTrainingTopics = () => request<TrainingTopic[]>("GET", "/api/training/topics");
export const getTrainingPlan = (topicId: string) =>
  request<TrainingPlan>("GET", `/api/training/topics/${encodeURIComponent(topicId)}`);
export const getRefresher = () => request<Refresher>("GET", "/api/refresher/today");
export const sendFeedback = (fb: Feedback) => request<void>("POST", "/api/feedback", fb);
