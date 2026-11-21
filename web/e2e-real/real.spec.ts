import { expect, test, type Page } from "@playwright/test";
import { expectNoSeriousViolations } from "../e2e/helpers";

// Real mode against a local API with the stand-in model. One long story, because each step needs
// the one before it (request -> approve -> invite -> sign in -> use the app -> sign out).
const API = process.env.REAL_API ?? "http://localhost:8001";
const ADMIN = process.env.REAL_ADMIN_EMAIL ?? "real.admin@example.org";
const ADMIN_PW = process.env.REAL_ADMIN_PASSWORD ?? "";
const TEACHER = `real.teacher.${Date.now()}@example.org`;
const TEACHER_PW = "a-long-local-test-password";

async function signIn(page: Page, email: string, password: string) {
  await page.goto("/#/signin");
  await page.getByLabel("School email address").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
}

test.skip(!ADMIN_PW, "set REAL_ADMIN_PASSWORD (see playwright.real.config.ts)");

test("real mode: invite loop, then every screen against the API", async ({ page }) => {
  const calls: { url: string; method: string; auth?: string; body?: string }[] = [];
  page.on("request", (r) => {
    if (r.url().startsWith(API))
      calls.push({
        url: r.url().replace(API, ""),
        method: r.method(),
        auth: r.headers()["authorization"],
        body: r.postData() ?? undefined,
      });
  });

  // 1. Ask for access (job role is its own field)
  await page.goto("/#/request-access");
  await page.getByLabel("Your name").fill("Real Teacher");
  await page.getByLabel("School email address").fill(TEACHER);
  await page.getByLabel("District or school").fill("Local Elementary");
  await page.getByLabel("Your role").selectOption("Reading coach or interventionist");
  await page.getByRole("button", { name: "Send request" }).click();
  await expect(page).toHaveURL(/request-received/);
  const req = calls.find((c) => c.url === "/api/auth/request-access")!;
  expect(JSON.parse(req.body!)).toMatchObject({
    district: "Local Elementary",
    job_role: "Reading coach or interventionist",
  });

  // 2. Admin signs in, sees the request with its role, approves it
  await signIn(page, ADMIN, ADMIN_PW);
  await page.getByRole("link", { name: "Admin" }).click();
  await expect(page.getByRole("heading", { name: "Source review queue" })).toBeVisible();
  await page.getByRole("tab", { name: "Access requests" }).click();
  await expect(page.getByText("Local Elementary (Reading coach or interventionist)")).toBeVisible();
  await page.getByRole("button", { name: "Approve Real Teacher" }).click();
  const note = await page.getByRole("status").filter({ hasText: "Invite code:" }).textContent();
  const code = /Invite code: (\S+)\./.exec(note ?? "")?.[1];
  expect(code).toBeTruthy();
  // every admin call carried the bearer token
  const adminCalls = calls.filter(
    (c) => c.url.startsWith("/admin/") || c.url.includes("/api/admin/"),
  );
  expect(adminCalls.length).toBeGreaterThan(1);
  expect(adminCalls.every((c) => c.auth?.startsWith("Bearer "))).toBe(true);
  // Real sign-out is a network call: wait for its answer, or the app re-renders under the next form.
  const signedOut = page.waitForResponse((r) => r.url().includes("/api/auth/sign-out"));
  await page.getByRole("button", { name: "Sign out" }).click();
  await signedOut;
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Sign in to Reading Helper");

  // 3. The new teacher sets a password
  await page.getByRole("link", { name: "I have an invite code" }).click();
  // The form can reset once right after a real sign-out (observed in real mode only), so retry.
  await expect(async () => {
    await page.getByLabel("School email address").fill(TEACHER);
    await expect(page.getByLabel("School email address")).toHaveValue(TEACHER);
  }).toPass({ timeout: 10_000 });
  await page.getByLabel("Invite code").fill(code!);
  await page.getByLabel("New password").fill(TEACHER_PW);
  await page.getByRole("button", { name: "Set password and sign in" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("What do you want to work on?");
  await expectNoSeriousViolations(page);
  const token = await page.evaluate(() => window.sessionStorage.getItem("rh-token"));
  expect(token).toBeTruthy();

  // 4. Ask: a cited answer from the stand-in model, through the real verifier
  await page.getByLabel("Or just ask:").fill("How do I teach kindergartners to blend sounds?");
  await page.getByRole("button", { name: "Ask", exact: true }).click();
  await expect(page.getByText(/\[Fake model\]/).first()).toBeVisible({ timeout: 30_000 });
  await expect(page.getByRole("button", { name: /^Source 1:/ }).first()).toBeVisible();
  await expectNoSeriousViolations(page);
  await page.getByRole("button", { name: "It worked" }).click();
  await expect
    .poll(() => calls.find((c) => c.url === "/api/feedback")?.body)
    .toMatch(/"query_id":\d+/);

  // 5. Make a story: the server's marks, and a server re-check when a sound is turned off
  await page.goto("/#/teaching/story");
  await expect(page.getByTestId("story")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText("Every word checked")).toBeVisible();
  calls.length = 0;
  await page.getByRole("button", { name: "s", exact: true }).click(); // turn "s" off
  await expect.poll(() => calls.some((c) => c.url === "/api/decodable/check")).toBe(true);
  await expect(page.getByTestId("story").locator('[data-status="unknown"]').first()).toBeVisible();
  await expect(page.getByRole("button", { name: "Print this story" })).toBeDisabled();
  await expectNoSeriousViolations(page);

  // 6. Why is a kid stuck? A real pattern, then a name is refused by the server
  await page.goto("/#/teaching/stuck");
  await page.getByRole("button", { name: "ship → sip" }).click();
  await page.getByRole("button", { name: "Find the skill" }).click();
  await expect(page.getByText(/\[Fake model\]/).first()).toBeVisible({ timeout: 30_000 });
  await page.getByLabel("The word").fill("Jamal");
  await page.getByLabel("What they said").fill("jam");
  await page.getByRole("button", { name: "Find the skill" }).click();
  await expect(page.getByText(/No names/i)).toBeVisible();

  // 7. Tomorrow's groups -> a group plan
  await page.goto("/#/teaching/groups/g-b");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(/Group B/, { timeout: 30_000 });
  await expect(page.getByText(/\[Fake model\]/).first()).toBeVisible();
  await expectNoSeriousViolations(page);

  // 8. My training and the 1-minute refresher
  await page.goto("/#/training");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "Turn your training into practice",
  );
  await page
    .getByRole("link", { name: /Turn into a plan/ })
    .first()
    .click();
  await expect(page.getByText(/\[Fake model\]/).first()).toBeVisible({ timeout: 30_000 });
  await page.goto("/#/training/refreshers");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Grow at your own pace");

  // 9. A teacher cannot open Admin; every signed-in call carried the token
  await page.goto("/#/admin");
  await expect(page.getByRole("heading", { name: "Source review queue" })).toHaveCount(0);
  const apiCalls = calls.filter((c) => c.url.startsWith("/api/") && !c.url.includes("/auth/sign"));
  expect(apiCalls.length).toBeGreaterThan(0);
  expect(apiCalls.every((c) => c.auth?.startsWith("Bearer "))).toBe(true);

  // 10. Sign out really ends the session on the server
  await page.goto("/#/");
  await page.getByRole("button", { name: "Sign out" }).click();
  const me = await page.request.get(`${API}/api/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(me.status()).toBe(401);
});
