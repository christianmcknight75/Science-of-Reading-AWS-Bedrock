# Reading Helper API contract

Single source of truth for every endpoint the teacher app calls. Code that disagrees with this file is a bug in the code or in this file: fix one of them in the same PR. Types are TypeScript for the frontend; the server models are in `api/app/schemas.py`, `api/app/features.py` and `api/app/accounts.py`.

Status of the Phase 4 endpoints: **built against a fake model client, never run against a real model** (both allowed Claude models are blocked by the org SCP, see `docs/OPEN_QUESTIONS.md` 15). Everything is behind the `QA_ENABLED` kill switch, which is **off by default**.

## Rules every endpoint follows
- **Auth:** `Authorization: Bearer <access token>` on everything except `/health`, `POST /api/auth/request-access`, `POST /api/auth/sign-in`, `POST /api/auth/accept-invite` and the dev issuer's JWKS. The current `web/src/api/client.ts` sends no Authorization header; it must add one.
- **Errors:** always `{"detail": "<teacher-ready sentence>"}` with an HTTP status (client already reads `detail`). `401` not signed in, `403` not allowed, `404` unknown id, `422` bad input (detail is a plain sentence, not a validation list), `429` too many requests (including sign-in), `503` switched off or the answer could not be fully supported.
- **No source, no claim:** every statement under "research says" cites passages that were retrieved for that request. Server checks: cited ids were retrieved, each claim's quote appears verbatim in a cited passage, a claim check says the passage supports it. Failing claims are removed; if too little remains the endpoint returns `503` with an honest sentence. Fields documented as *idea* are our suggestions and are never presented as research.
- **Evidence label** is computed by code (`api/app/evidence.py`), never by the model.
- **Every feature response carries** `disclaimer` (string, always shown), `content_last_updated` (ISO date or null) and `query_id` (number or null; pass it to `/api/feedback`).
- **No student data.** No names, scores or assessment results are accepted or stored. Free text is redacted (Presidio) before it is logged or sent to a model. Group labels, mistakes and stories never leave the teacher's device except as the minimal request below.
- **Logging:** `query_log` stores redacted text only (Public Records Act). Mistake pairs are not logged, only their count and the pattern found.

## Shared types
```ts
type EvidenceLabel = "Very sure" | "Fairly sure" | "Not sure yet" | "No research found";
type Grade = "K" | "1" | "2" | "3";
type Skill = "hear-sounds" | "blend" | "digraphs" | "tricky-words";

interface ResearchClaim { text: string; citations: number[] }        // numbers refer to sources[].n
interface SourceOut { n: number; passage_id: string; title: string; year: number | null;
  source_type: string; section: string | null; page: string | null;  // printed page label
  passage_text: string; quote: string | null }                       // quote is always inside passage_text
interface StepOut { text: string; minutes: number }
interface Meta { disclaimer: string; content_last_updated: string | null; query_id: number | null }
```

## Q&A (built)
`POST /api/ask` body `{question: string (1-1000), grade?: Grade}` -> `AnswerResponse` (`api/app/schemas.py`; unchanged). `kind` is `answer | no_research | insufficient | out_of_scope | unavailable`. **Change vs the frontend's types:** `query_id` was added to `AnswerResponse`.

## Group plan
`POST /api/group-plan` body `{focus: Skill, sounds: string[] (0-12 items, each 1-4 letters, "a_e" allowed), grade?: Grade}`

```ts
interface PlanStep { title: string; minutes: number; body: string;
  words?: string[];   // practice words: every one passed the decodability checker (or is a listed heart word for "tricky-words")
  sounds?: string[]; story?: string[]; tip?: string; alt?: { title: string; body: string } }
interface GroupPlan extends Meta { minutes: number;        // sum of steps
  why: string;                                             // the first verified research claim, cited
  evidence_label: EvidenceLabel; research_says: ResearchClaim[]; steps: PlanStep[]; // steps are IDEAS
  sources: SourceOut[] }
```
Groups themselves (label, size) stay on the teacher's device; the server never receives them.

## Story ("Make a story")
`POST /api/story` body `{sounds: string[] (1-12), about?: string (<= 60 chars, redacted), variant?: number (0-9), heart_words?: string[] (<= 20)}`

```ts
interface WordCheck { word: string; status: "decodable" | "heart_word" | "not_decodable" | "unknown";
  decodable: boolean;        // true ONLY for status "decodable"; a heart word is allowed but never labelled decodable
  reason: string; graphemes: string[]; needs: string[] }
interface Story extends Meta { title: string; words: string[];    // reading order
  checks: WordCheck[];       // same length and order as words
  all_decodable: boolean;    // every word is decodable or a listed heart word
  flagged: string[];         // words that are not_decodable or unknown
  evidence_label: EvidenceLabel; research_says: ResearchClaim[]; sources: SourceOut[] }
```
The server asks the model for a story, checks every word in plain code (CMU Pronouncing Dictionary + grapheme-phoneme rules + the taught sounds; no AI), and asks for a repair up to 2 times. If words still fail, the story is returned with `all_decodable: false` and the failing words in `flagged`; the app must highlight them and must not call the story decodable. **Changes vs the frontend's types:** `words` stays `string[]`; `checks`, `all_decodable`, `flagged`, `evidence_label`, `research_says` and `Meta` were added.

`POST /api/decodable/check` body `{sounds: string[], words: string[] (<= 200), heart_words?: string[]}` -> `{checks: WordCheck[]}`. Used when a teacher edits or adds her own words.

## Why is a kid stuck?
`POST /api/stuck` body `{pairs: {word: string; said: string}[] (1-8)}`. `word` and `said` are letters only (an apostrophe allowed), at most 20 characters. Anything that looks like a name is refused with `422`.

```ts
interface MistakeResult extends Meta { kind: "match" | "no_match"; pattern: string; skill: string;
  try_it: StepOut | null;        // IDEA
  also_watch: string;            // IDEA
  evidence_label: EvidenceLabel; evidence_note: string;   // plain-words explanation of the label
  research_says: ResearchClaim[];                         // added: the cited basis
  sources: SourceOut[]; message: string }
```
Patterns come from code rules (`api/app/stuck.py`), a **draft** until the SME's error-pattern list arrives (open question 22). `no_match` returns an honest message and no research.

## My training
`GET /api/training/topics` -> `TrainingTopic[]`: `{id, title, summary, training_word, fits}` (draft topic list, `api/seed/training_topics.json`).
`GET /api/training/topics/{id}` -> `TrainingPlan` (`404` for an unknown id):
```ts
interface TrainingPlan extends Meta { topic: TrainingTopic;
  remember: { sentence: string; sounds: { letter: string; hint: string }[]; tip: string }; // sentence = first verified claim (cited)
  evidence_label: EvidenceLabel; research_says: ResearchClaim[];
  idea: { title: string; minutes: number; steps: string[]; need: string };        // IDEAS from here down
  short_idea: { title: string; minutes: number; steps: string[]; need: string };
  if_stuck: string; if_easy: string; for_english_learners: string; sources: SourceOut[] }
```
**Change:** `Meta` added; `remember.sounds`/`tip`, `idea`, `short_idea`, `if_stuck`, `if_easy` and `for_english_learners` are ideas, not research, and the app should show them under "Idea for your class".

## 1-minute refresher
`GET /api/refresher/today` -> `Refresher`:
```ts
interface Refresher extends Meta { day: number;       // 1-5, repeats
  statement: string; is_true: boolean; explanation: string; citations: number[]; // explanation is a verified, cited claim
  sources: SourceOut[]; skills: string[];
  picked: { minutes: number; kind: string; title: string; you_get: string }[] }   // static, from the topic
```
`is_true` is always `true` for now: statements are the verified claim itself. False statements need myths with SME-approved passage links (open question 19). **Open:** I did not know what `picked` is for; it is served from static topic data.

## Feedback
`POST /api/feedback` body `{rating: "worked" | "so-so" | "stuck", query_id?: number}` -> `204`. Stored on the `query_log` row (or as its own row without a question when `query_id` is missing or unknown). **Change:** `query_id` added.

## Accounts (closed access, no public sign-up)
Tables: `users` (name, school email, district, role teacher|admin, status active|disabled), `access_requests` (pending|approved|denied) and `access_audit` (every status change: who, when, from, to, reason; a database trigger refuses a status change without actor and reason, like `source_audit`).

Tokens are JWTs verified exactly as Cognito tokens will be: RS256 only, signature from the issuer's JWKS (by `kid`), `iss` must equal the configured issuer, `client_id` (access token) or `aud` (id token) must equal the app client, `token_use: access`, `exp` required, `jti` not revoked. Claims: `sub`, `username` (email), `cognito:groups` (`["admin"]` for admins), `jti`, `iat`, `exp`. For now the **local dev issuer** signs them (`AUTH_MODE=local`; key generated under `data/local/`, JWKS at `/dev-issuer/.well-known/jwks.json`). In Phase 5 only the issuer, client id and JWKS URL settings change to Cognito's; `/api/auth/sign-in`, `accept-invite` and `sign-out` are replaced by Cognito's hosted flows. Access tokens last 60 minutes; there is no refresh token yet.

| Endpoint | Body -> response |
|---|---|
| `POST /api/auth/request-access` (public, 3 per hour per address) | `{name, email, district}` -> `202 {message}`. The same answer whether or not the email is known, so it cannot be used to find out who has an account. A second pending request from the same email is ignored. |
| `GET /api/admin/access-requests?status=pending` (admin) | -> `AccessRequest[]` `{request_id, name, email, district, status, requested_at, decided_by, decided_at, decision_reason}` |
| `POST /api/admin/access-requests/{id}/approve` (admin) | `{role?: "teacher" \| "admin", reason?}` -> `{user_id, invite_code}`. Creates the user (status `active`, no password yet). The one-time `invite_code` (valid 24 h, stored only as a hash) is shown to the admin once; in production it is emailed by Cognito instead. |
| `POST /api/admin/access-requests/{id}/deny` (admin) | `{reason}` (required) -> `204` |
| `POST /api/auth/accept-invite` (public) | `{email, invite_code, password (>= 12 chars)}` -> same as sign-in. Sets the password (scrypt hash, per-user salt). **Added; not in the original list.** |
| `POST /api/auth/sign-in` (public, rate limited) | `{email, password}` -> `{access_token, token_type: "Bearer", expires_in: 3600, user: Me}`. 5 failures per 15 minutes per email and per address, then `429`. The same `401` message for a wrong password, an unknown email and a disabled user. |
| `POST /api/auth/sign-out` | -> `204`. Revokes the token's `jti`. |
| `GET /api/auth/me` | -> `Me` `{user_id, name, email, district, role, status}` |

Bootstrap: the first admin is created from the command line (`uv run python -m app.users create-admin --email ... --name ... --district ...`, password typed at a prompt), never by an endpoint.

## Open items
See `docs/OPEN_QUESTIONS.md` 20-26.
