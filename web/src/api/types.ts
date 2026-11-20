// Types for the teacher app's API.
//
// AnswerResponse, SourceOut, ResearchClaim, StepOut, WatchOut and AskRequest mirror
// api/app/schemas.py exactly (POST /api/ask is the only endpoint built so far).
// Everything below "PROPOSED" is the contract this app expects for the Phase 4 endpoints.
// It is not built yet: mock mode serves it, real mode calls it and shows a friendly error.

export type EvidenceLabel = "Very sure" | "Fairly sure" | "Not sure yet" | "No research found";
export type Grade = "K" | "1" | "2" | "3";

export interface AskRequest {
  question: string;
  grade?: Grade | null;
}

export interface ResearchClaim {
  text: string;
  citations: number[];
}

export interface SourceOut {
  n: number;
  passage_id: string;
  title: string;
  year: number | null;
  source_type: string; // practice_guide | meta_analysis | study | foundational
  section: string | null;
  page: string | null; // printed page label
  passage_text: string;
  quote: string | null; // exact span used; always inside passage_text
}

export interface StepOut {
  text: string;
  minutes: number;
}

export interface WatchOut {
  myth: string;
  correction: string;
  citations: number[];
}

export interface AnswerResponse {
  kind: "answer" | "no_research" | "insufficient" | "out_of_scope" | "unavailable";
  evidence_label: string;
  mixed: boolean;
  short_answer: string;
  research_says: ResearchClaim[];
  idea_for_class: StepOut[];
  watch_out: WatchOut | null;
  sources: SourceOut[];
  message: string;
  offer: string;
  disclaimer: string;
  content_last_updated: string | null;
  query_id: number | null; // pass to sendFeedback
}

/** On every feature response (docs/API_CONTRACT.md "Rules every endpoint follows"). */
export interface Meta {
  disclaimer: string;
  content_last_updated: string | null;
  query_id: number | null;
}

/** Added by mock mode only. The UI shows an "Example" marker whenever this is true. */
export interface Marked {
  example?: boolean;
}
export type AskResult = AnswerResponse & Marked;

// ---------------------------------------------------------------- PROPOSED (Phase 4)

export type Skill = "hear-sounds" | "blend" | "digraphs" | "tricky-words";

/** Held on the teacher's device only. The label is free text such as "Group A". Never a name. */
export interface Group {
  id: string;
  label: string;
  size: number | null;
  focus: Skill;
}

export interface PlanStep {
  title: string;
  minutes: number;
  body: string;
  words?: string[]; // practice words (class board)
  sounds?: string[];
  story?: string[]; // words of a decodable story
  tip?: string;
  alt?: { title: string; body: string }; // what "Swap this step" shows instead
}

export interface GroupPlan extends Marked, Meta {
  minutes: number;
  why: string;
  evidence_label: string;
  mixed: boolean; // cited evidence disagrees; the label is then at most "Not sure yet"
  research_says: ResearchClaim[];
  steps: PlanStep[];
  sources: SourceOut[];
}

export interface StoryRequest {
  sounds: string[];
  about?: string;
  variant?: number; // 0, 1, 2...: ask for a different story than last time
}
/** The server's decodability check of one word (CMU dictionary + grapheme rules, no AI). */
export interface WordCheck {
  word: string;
  status: "decodable" | "heart_word" | "not_decodable" | "unknown";
  decodable: boolean; // true ONLY for "decodable"; a heart word is allowed but never "decodable"
  reason: string;
  graphemes: string[];
  needs: string[]; // untaught graphemes a failing word needs
}
export interface DecodableCheckRequest {
  sounds: string[];
  words: string[];
  heart_words?: string[];
}
export interface Story extends Marked, Meta {
  title: string;
  words: string[]; // in reading order
  checks: WordCheck[]; // same length and order as words: the server's marks
  all_decodable: boolean;
  flagged: string[]; // words that are not_decodable or unknown
  evidence_label: string;
  mixed: boolean;
  research_says: ResearchClaim[];
  sources: SourceOut[];
}

export interface MistakePair {
  word: string;
  said: string;
}
export interface MistakeResult extends Marked, Meta {
  kind: "match" | "no_match";
  pattern: string;
  skill: string;
  try_it: StepOut | null;
  also_watch: string;
  evidence_label: string;
  evidence_note: string;
  research_says: ResearchClaim[]; // the cited basis (empty for no_match)
  sources: SourceOut[];
  message: string;
}

export interface TrainingTopic {
  id: string;
  title: string;
  summary: string;
  training_word: string;
  fits: string;
}
export interface TrainingPlan extends Marked, Meta {
  topic: TrainingTopic;
  remember: { sentence: string; sounds: { letter: string; hint: string }[]; tip: string };
  evidence_label: string;
  mixed: boolean;
  research_says: ResearchClaim[];
  idea: { title: string; minutes: number; steps: string[]; need: string };
  short_idea: { title: string; minutes: number; steps: string[]; need: string };
  if_stuck: string;
  if_easy: string;
  for_english_learners: string;
  sources: SourceOut[];
}

export interface Refresher extends Marked, Meta {
  day: number;
  statement: string;
  is_true: boolean;
  explanation: string;
  citations: number[];
  sources: SourceOut[];
  skills: string[];
  evidence_label: string;
  picked: { minutes: number; kind: string; title: string; you_get: string }[];
}

export interface Feedback {
  rating: "worked" | "so-so" | "stuck";
  query_id?: number | null; // from the answer being rated; sent only when known
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

// ---------------------------------------------------------------- Accounts
// Matches ../Science-of-Reading-AWS-Bedrock/docs/API_CONTRACT.md "Accounts (closed access)".
// Server models (api/app/accounts.py) were not written yet when this was built.
export type Role = "teacher" | "admin";

export interface Me {
  user_id: number | string;
  name: string;
  email: string;
  district: string;
  role: Role;
  status: "active" | "disabled";
}
export interface SignInResult {
  access_token: string;
  token_type: "Bearer";
  expires_in: number;
  user: Me;
}
export interface RequestAccessBody {
  name: string;
  email: string;
  district: string; // district or school
  job_role?: string; // "Reading coach" etc. Information for the reviewing admin, not a permission
}
export type RequestStatus = "pending" | "approved" | "denied";
export interface AccessRequest {
  request_id: number | string;
  name: string;
  email: string;
  district: string;
  job_role: string | null;
  status: RequestStatus;
  requested_at: string;
  decided_by: string | null;
  decided_at: string | null;
  decision_reason: string | null;
}
export interface ApproveResult {
  user_id: number | string;
  invite_code: string; // shown to the admin once; production emails it instead
}
