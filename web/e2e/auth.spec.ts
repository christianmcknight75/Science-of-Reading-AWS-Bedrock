import { expect, test } from "@playwright/test";
import {
  anon,
  asAdmin,
  expectFooter,
  expectNoHorizontalScroll,
  expectNoSeriousViolations,
  expectTargets,
  fast,
} from "./helpers";

const PUBLIC: { name: string; hash: string; h1: string }[] = [
  { name: "Sign in", hash: "#/signin", h1: "Sign in to Reading Helper" },
  { name: "Request access", hash: "#/request-access", h1: "Request access" },
  { name: "Request received", hash: "#/request-received", h1: "We've got your request" },
  { name: "Forgot password", hash: "#/forgot-password", h1: "Forgot your password?" },
  { name: "Check your email", hash: "#/forgot-sent", h1: "Check your email" },
  { name: "Set your password", hash: "#/accept-invite", h1: "Set your password" },
];
for (const s of PUBLIC) {
  test(`${s.name}: accessible, footer, targets >= 48px, no sideways scroll`, async ({ page }) => {
    await anon(page);
    await page.goto(`/${s.hash}`);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(s.h1);
    await expectFooter(page);
    await expectNoSeriousViolations(page);
    await expectTargets(page);
    await expectNoHorizontalScroll(page);
  });
}

test("every app route needs sign-in, then returns you where you were going", async ({ page }) => {
  await anon(page);
  await page.goto("/#/teaching/groups");
  await expect(page).toHaveURL(/#\/signin\?next=%2Fteaching%2Fgroups/);
  await page.getByLabel("School email address").fill("demo.teacher@example.org");
  await page.getByLabel("Password", { exact: true }).fill("example-password-1");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/#\/teaching\/groups$/);
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Tomorrow");
});

test("signed-out visitors cannot reach any teacher screen", async ({ page }) => {
  await anon(page);
  for (const h of ["#/", "#/ask?q=x", "#/training", "#/settings", "#/board", "#/admin"]) {
    await page.goto(`/${h}`);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Sign in to Reading Helper");
  }
});

test("sign in: empty form shows an error summary that links to the fields", async ({ page }) => {
  await anon(page);
  await page.goto("/#/signin");
  await page.getByRole("button", { name: "Sign in" }).click();
  const alert = page.getByRole("alert");
  await expect(alert).toBeFocused();
  await expect(alert).toContainText("Enter your school email address");
  await alert.getByRole("link", { name: "Enter your password" }).click();
  await expect(page.getByLabel("Password", { exact: true })).toBeFocused();
  await expectNoSeriousViolations(page);
});

test("sign in: wrong details get one message that does not say which part was wrong", async ({
  page,
}) => {
  await anon(page);
  await page.goto("/#/signin");
  await page.getByLabel("School email address").fill("demo.teacher@example.org");
  await page.getByLabel("Password", { exact: true }).fill("nope-nope-nope");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("alert")).toContainText("email or password did not match");
  await page.getByLabel("School email address").fill("nobody@example.org");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("alert")).toContainText("email or password did not match");
  await expectNoSeriousViolations(page);
});

test("teacher: signs in, has no Admin link, cannot open admin, signs out", async ({ page }) => {
  await anon(page);
  await page.goto("/#/signin");
  await page.getByLabel("School email address").fill("demo.teacher@example.org");
  await page.getByLabel("Password", { exact: true }).fill("example-password-1");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("What do you want to work on?");
  const nav = page.getByRole("navigation", { name: "Main" });
  await expect(nav.getByRole("link", { name: "Admin" })).toHaveCount(0);
  await page.goto("/#/admin");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("don't have access");
  await expectNoSeriousViolations(page);
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/#\/signin\?signedout=1/);
  await expect(page.getByText("You have signed out.")).toBeVisible();
  await page.goto("/#/");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Sign in to Reading Helper");
});

test("request access: validates, then confirms; no public sign-up", async ({ page }) => {
  await anon(page);
  await page.goto("/#/request-access");
  await page.getByRole("button", { name: "Send request" }).click();
  const alert = page.getByRole("alert");
  await expect(alert).toContainText("Enter your name");
  await expect(alert).toContainText("Choose your role");
  await expectNoSeriousViolations(page);
  await page.getByLabel("Your name").fill("Example Person");
  await page.getByLabel("School email address").fill("example.person@example.org");
  await page.getByLabel("District or school").fill("Example Elementary");
  await page.getByLabel("Your role").selectOption("Classroom teacher");
  await page.getByRole("button", { name: "Send request" }).click();
  await expect(page).toHaveURL(/#\/request-received/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("We've got your request");
});

test("forgot password gives the same answer for any address", async ({ page }) => {
  await anon(page);
  await page.goto("/#/forgot-password");
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page.getByRole("alert")).toContainText("Enter your school email address");
  await page.getByLabel("School email address").fill("anyone@example.org");
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page.getByText(/nobody can use this page to find out/)).toBeVisible();
});

test("admin: access requests tab approves with a one-time code and requires a reason to deny", async ({
  page,
}) => {
  await asAdmin(page);
  await page.goto("/#/admin");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Admin");
  await expect(page.getByRole("tab", { name: "Source queue" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  await page.getByRole("tab", { name: "Access requests" }).click();
  await expect(page.getByRole("heading", { name: "Example Teacher One" })).toBeVisible();
  await expectNoSeriousViolations(page);
  await expectTargets(page);

  await page.getByRole("button", { name: "Approve Example Teacher One" }).click();
  await expect(page.getByRole("status").filter({ hasText: "Invite code:" })).toContainText(
    "shown once",
  );
  await expect(page.getByRole("heading", { name: "Example Teacher One" })).toHaveCount(0);

  await page.getByRole("button", { name: "Deny Example Coach Two" }).click();
  await page.getByRole("button", { name: "Confirm deny" }).click();
  await expect(page.getByRole("alert")).toContainText("reason");
  await page.getByLabel("Reason for denying (required)").fill("Not a school address");
  await page.getByRole("button", { name: "Confirm deny" }).click();
  await expect(
    page.getByRole("status").filter({ hasText: "Denied Example Coach Two" }),
  ).toBeVisible();

  await page.getByRole("button", { name: "Denied" }).click();
  await expect(page.getByText(/reason: Not a school address/)).toBeVisible();
  await expectNoSeriousViolations(page);
});

test("full invite loop: request -> admin approves -> new teacher sets a password and signs in", async ({
  page,
}) => {
  await anon(page);
  await page.goto("/#/request-access");
  await page.getByLabel("Your name").fill("Loop Person");
  await page.getByLabel("School email address").fill("loop.person@example.org");
  await page.getByLabel("District or school").fill("Loop School");
  await page.getByLabel("Your role").selectOption("Reading coach or interventionist");
  await page.getByRole("button", { name: "Send request" }).click();
  await expect(page).toHaveURL(/request-received/);

  await page.goto("/#/signin");
  await page.getByLabel("School email address").fill("demo.admin@example.org");
  await page.getByLabel("Password", { exact: true }).fill("example-password-2");
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByRole("link", { name: "Admin" }).click();
  await page.getByRole("tab", { name: "Access requests" }).click();
  // The job role is its own field now (not squeezed into the district text).
  await expect(page.getByText("Loop School (Reading coach or interventionist)")).toBeVisible();
  await page.getByRole("button", { name: "Approve Loop Person" }).click();
  const note = await page.getByRole("status").filter({ hasText: "Invite code:" }).textContent();
  const code = /Invite code: (\S+)\./.exec(note ?? "")?.[1];
  expect(code).toBeTruthy();

  await page.getByRole("button", { name: "Sign out" }).click();
  await page.getByRole("link", { name: "I have an invite code" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Set your password");
  await page.getByLabel("School email address").fill("loop.person@example.org");
  await page.getByLabel("Invite code").fill(code!);
  await page.getByLabel("New password").fill("a-long-new-password");
  await page.getByRole("button", { name: "Set password and sign in" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("What do you want to work on?");
});

test("no sign-in form asks for a student", async ({ page }) => {
  await anon(page);
  for (const h of ["#/signin", "#/request-access", "#/accept-invite", "#/forgot-password"]) {
    await page.goto(`/${h}`);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await expect(page.getByLabel(/student/i)).toHaveCount(0);
  }
});

// ---- Motion and mascot rules -----------------------------------------------------------------
test("motion: cards animate normally, and stop with the OS setting and the in-app switch", async ({
  page,
}) => {
  await fast(page);
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await page.goto("/#/");
  const card = page.locator("main .rh-card").first();
  await expect(card).toBeVisible();
  const name = () => card.evaluate((el) => getComputedStyle(el).animationName);
  const dur = () => card.evaluate((el) => parseFloat(getComputedStyle(el).animationDuration));
  expect(await name()).toBe("rh-rise");
  expect(await dur()).toBeGreaterThan(0.1);

  await page.emulateMedia({ reducedMotion: "reduce" });
  expect(await dur()).toBeLessThan(0.001);

  await page.emulateMedia({ reducedMotion: "no-preference" });
  await page.goto("/#/settings");
  await page.getByRole("switch", { name: "Less moving and animation" }).check();
  await page.goto("/#/");
  expect(await dur()).toBeLessThan(0.001);
});

test("mascot: decorative, on Home and empty states, never inside an answer", async ({ page }) => {
  await fast(page);
  await page.goto("/#/");
  await expect(page.getByTestId("mascot")).toHaveCount(1);
  await expect(page.getByTestId("mascot")).toHaveAttribute("aria-hidden", "true");

  await page.goto("/#/ask?q=How%20do%20I%20grow%20tomatoes");
  await expect(page.getByRole("heading", { name: "No research found" })).toBeVisible();
  await expect(page.getByTestId("mascot")).toHaveCount(1);

  await page.goto("/#/ask?q=My%20kids%20know%20letter%20sounds%20but%20can't%20read%20words");
  await expect(page.getByTestId("evidence-label")).toBeVisible();
  await expect(page.getByTestId("mascot")).toHaveCount(0);
  await page
    .getByRole("button", { name: /^Source 1:/ })
    .first()
    .click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByTestId("mascot")).toHaveCount(0);
});
