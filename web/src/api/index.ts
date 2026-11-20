// One switch for the whole app: VITE_API_MODE=mock (default) or real.
// Screens import from "../api" and never know which one they got.
import * as real from "./client";
import * as mock from "./mock";

export * from "./types";

export const API_MODE: "mock" | "real" = import.meta.env.VITE_API_MODE === "real" ? "real" : "mock";
export const IS_MOCK = API_MODE === "mock";

import * as mockAuth from "./mockAuth";

const impl = IS_MOCK ? mock : real;
const auth = IS_MOCK ? mockAuth : real;
export const ask = impl.ask;
export const getGroupPlan = impl.getGroupPlan;
export const makeStory = impl.makeStory;
export const diagnoseMistakes = impl.diagnoseMistakes;
export const listTrainingTopics = impl.listTrainingTopics;
export const getTrainingPlan = impl.getTrainingPlan;
export const getRefresher = impl.getRefresher;
export const sendFeedback = impl.sendFeedback;

export const signIn = auth.signIn;
export const signOutApi = auth.signOutApi;
export const getMe = auth.getMe;
export const acceptInvite = auth.acceptInvite;
export const requestAccess = auth.requestAccess;
export const listAccessRequests = auth.listAccessRequests;
export const approveAccessRequest = auth.approveAccessRequest;
export const denyAccessRequest = auth.denyAccessRequest;
export { MOCK_ACCOUNTS } from "./mockAuth";
export { clearToken, getToken, setToken } from "./session";

export const DISCLAIMER = mock.MOCK_DISCLAIMER; // same wording as api/app/schemas.py DISCLAIMER
export const OFFER = mock.MOCK_OFFER;
/** Footer date. In real mode set VITE_CONTENT_LAST_UPDATED at build time (ISO date). */
export const CONTENT_LAST_UPDATED: string =
  import.meta.env.VITE_CONTENT_LAST_UPDATED ?? mock.MOCK_CONTENT_DATE;
