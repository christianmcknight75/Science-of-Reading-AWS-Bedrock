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

export interface GroupPlan extends Marked {
  minutes: number;
  why: string;
  evidence_label: string;
  research_says: ResearchClaim[];
  steps: PlanStep[];
  sources: SourceOut[];
}

export interface StoryRequest {
  sounds: string[];
  about?: string;
  variant?: number; // 0, 1, 2...: ask for a different story than last time
}
export interface Story extends Marked {
  title: string;
  words: string[]; // in reading order; the checker marks each word
  sources: SourceOut[];
}

export interface MistakePair {
  word: string;
  said: string;
}
export interface MistakeResult extends Marked {
  kind: "match" | "no_match";
  pattern: string;
  skill: string;
  try_it: StepOut | null;
  also_watch: string;
  evidence_label: string;
  evidence_note: string;
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
export interface TrainingPlan extends Marked {
  topic: TrainingTopic;
  remember: { sentence: string; sounds: { letter: string; hint: string }[]; tip: string };
  evidence_label: string;
  research_says: ResearchClaim[];
  idea: { title: string; minutes: number; steps: string[]; need: string };
  short_idea: { title: string; minutes: number; steps: string[]; need: string };
  if_stuck: string;
  if_easy: string;
  for_english_learners: string;
  sources: SourceOut[];
}

export interface Refresher extends Marked {
  day: number;
  statement: string;
  is_true: boolean;
  explanation: string;
  citations: number[];
  sources: SourceOut[];
  skills: string[];
  picked: { minutes: number; kind: string; title: string; you_get: string }[];
}

export interface Feedback {
  rating: "worked" | "so-so" | "stuck";
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}
