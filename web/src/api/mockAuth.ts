// Mock accounts for example mode. Everything here is clearly fake (example.org addresses).
// Passwords are shown on the sign-in screen in example mode; they unlock nothing real.
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
} from "./types";

export const MOCK_ACCOUNTS = [
  {
    email: "demo.teacher@example.org",
    password: "example-password-1",
    name: "Demo Teacher",
    role: "teacher" as Role,
  },
  {
    email: "demo.admin@example.org",
    password: "example-password-2",
    name: "Demo Admin",
    role: "admin" as Role,
  },
];

interface MockUser extends Me {
  password: string;
}
const USERS = "rh-mock-users";
const REQS = "rh-mock-requests";
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
const delay = () => sleep((window as unknown as { __MOCK_DELAY__?: number }).__MOCK_DELAY__ ?? 500);

function read<T>(key: string, fallback: T): T {
  try {
    const raw = window.localStorage.getItem(key);
    if (raw) return JSON.parse(raw) as T;
  } catch {
    /* ignore */
  }
  return fallback;
}
function write(key: string, v: unknown) {
  try {
    window.localStorage.setItem(key, JSON.stringify(v));
  } catch {
    /* ignore */
  }
}

const users = (): MockUser[] =>
  read<MockUser[]>(
    USERS,
    MOCK_ACCOUNTS.map((a, i) => ({
      user_id: i + 1,
      name: a.name,
      email: a.email,
      password: a.password,
      district: "Example School District",
      role: a.role,
      status: "active" as const,
    })),
  );

const SEED: AccessRequest[] = [
  {
    request_id: 101,
    name: "Example Teacher One",
    email: "teacher.one@example.org",
    district: "Example Elementary (Classroom teacher)",
    status: "pending",
    requested_at: "2026-11-18T14:05:00Z",
    decided_by: null,
    decided_at: null,
    decision_reason: null,
  },
  {
    request_id: 102,
    name: "Example Coach Two",
    email: "coach.two@example.org",
    district: "Sample County Schools (Reading coach)",
    status: "pending",
    requested_at: "2026-11-19T09:40:00Z",
    decided_by: null,
    decided_at: null,
    decision_reason: null,
  },
  {
    request_id: 103,
    name: "Example Teacher Three",
    email: "teacher.three@example.org",
    district: "Sample Elementary (Classroom teacher)",
    status: "approved",
    requested_at: "2026-11-10T11:00:00Z",
    decided_by: "demo.admin@example.org",
    decided_at: "2026-11-11T08:00:00Z",
    decision_reason: null,
  },
];
const requests = () => read<AccessRequest[]>(REQS, SEED);

const toMe = (u: MockUser): Me => ({
  user_id: u.user_id,
  name: u.name,
  email: u.email,
  district: u.district,
  role: u.role,
  status: u.status,
});

export async function signIn(email: string, password: string): Promise<SignInResult> {
  await delay();
  const u = users().find((x) => x.email.toLowerCase() === email.trim().toLowerCase());
  // One message for every failure, like the real endpoint.
  if (!u || u.password !== password || u.status !== "active")
    throw new ApiError("That email or password did not match. Check them and try again.", 401);
  const token = `mock.${u.user_id}`;
  setToken(token);
  return { access_token: token, token_type: "Bearer", expires_in: 3600, user: toMe(u) };
}
export async function getMe(): Promise<Me> {
  const t = getToken();
  const u = users().find((x) => `mock.${x.user_id}` === t);
  if (!u) throw new ApiError("Please sign in.", 401);
  return toMe(u);
}
export async function signOutApi(): Promise<void> {
  clearToken();
}
export async function acceptInvite(
  email: string,
  code: string,
  password: string,
): Promise<SignInResult> {
  await delay();
  const list = users();
  const u = list.find((x) => x.email.toLowerCase() === email.trim().toLowerCase());
  if (!u || code.trim() !== `EXAMPLE-${u.user_id}`)
    throw new ApiError(
      "That invite code did not work. Check it, or ask your administrator for a new one.",
      401,
    );
  if (password.length < 12)
    throw new ApiError("Choose a password with at least 12 characters.", 422);
  u.password = password;
  write(USERS, list);
  return signIn(email, password);
}
export async function requestAccess(b: RequestAccessBody): Promise<{ message: string }> {
  await delay();
  const list = requests();
  if (!list.some((r) => r.email === b.email && r.status === "pending"))
    write(REQS, [
      ...list,
      {
        request_id: Date.now(),
        name: b.name,
        email: b.email,
        district: b.district,
        status: "pending",
        requested_at: new Date().toISOString(),
        decided_by: null,
        decided_at: null,
        decision_reason: null,
      },
    ]);
  // Same answer whether or not the address is known.
  return { message: "Thanks. An administrator will review your request." };
}
export async function listAccessRequests(status: RequestStatus): Promise<AccessRequest[]> {
  await delay();
  return requests().filter((r) => r.status === status);
}
export async function approveAccessRequest(
  id: AccessRequest["request_id"],
  role: Role = "teacher",
): Promise<ApproveResult> {
  await delay();
  const list = requests();
  const r = list.find((x) => x.request_id === id);
  if (!r) throw new ApiError("We couldn't find that request.", 404);
  r.status = "approved";
  r.decided_by = "demo.admin@example.org";
  r.decided_at = new Date().toISOString();
  write(REQS, list);
  const us = users();
  const user_id = us.length + 1;
  us.push({
    user_id,
    name: r.name,
    email: r.email,
    password: "",
    district: r.district,
    role,
    status: "active",
  });
  write(USERS, us);
  return { user_id, invite_code: `EXAMPLE-${user_id}` };
}
export async function denyAccessRequest(
  id: AccessRequest["request_id"],
  reason: string,
): Promise<void> {
  await delay();
  if (!reason.trim()) throw new ApiError("Please give a short reason.", 422);
  const list = requests();
  const r = list.find((x) => x.request_id === id);
  if (!r) throw new ApiError("We couldn't find that request.", 404);
  r.status = "denied";
  r.decided_by = "demo.admin@example.org";
  r.decided_at = new Date().toISOString();
  r.decision_reason = reason.trim();
  write(REQS, list);
}
