import { expect, test } from "@playwright/test";
import {
  expectFooter,
  expectNoHorizontalScroll,
  expectNoSeriousViolations,
  expectTargets,
  fast,
  slow,
} from "./helpers";

// Every screen: heading, footer, 0 serious/critical axe issues, 48px targets, no sideways scroll.
const SCREENS: { name: string; hash: string; h1: string | RegExp }[] = [
  { name: "Home", hash: "#/", h1: "What do you want to work on?" },
  {
    name: "Answer",
    hash: "#/ask?q=My%20kids%20know%20letter%20sounds%20but%20can't%20read%20words",
    h1: /letter sounds/,
  },
  { name: "Answer: no research", hash: "#/ask?q=How%20do%20I%20grow%20tomatoes", h1: /tomatoes/ },
  { name: "Answer: out of scope", hash: "#/ask?q=Should%20I%20retain%20a%20student", h1: /retain/ },
  {
    name: "Answer: mixed evidence",
    hash: "#/ask?q=Are%20decodable%20books%20better",
    h1: /decodable/,
  },
];

for (const s of SCREENS) {
  test(`${s.name}: accessible, has footer, targets >= 48px`, async ({ page }) => {
    await fast(page);
    await page.goto(`/${s.hash}`);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(s.h1);
    await expectFooter(page);
    await expectNoSeriousViolations(page);
    await expectTargets(page);
    await expectNoHorizontalScroll(page);
  });
}

test("Behavior and Progress are off: not in the navigation, not on Home", async ({ page }) => {
  await fast(page);
  await page.goto("/#/");
  const nav = page.getByRole("navigation", { name: "Main" });
  await expect(nav.getByRole("link", { name: "Behavior" })).toHaveCount(0);
  await expect(page.getByText(/progress/i)).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Behavior" })).toHaveCount(0);
});

test("Home: Ask goes to the answer screen", async ({ page }) => {
  await fast(page);
  await page.goto("/#/");
  await page.getByLabel("Or just ask:").fill("My kids know letter sounds but can't read words");
  await page.getByRole("button", { name: "Ask", exact: true }).click();
  await expect(page).toHaveURL(/#\/ask\?q=/);
});

test("skip link moves focus to the main content", async ({ page }) => {
  await fast(page);
  await page.goto("/#/");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "Skip to main content" })).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("main")).toBeFocused();
});

const ASK = "#/ask?q=My%20kids%20know%20letter%20sounds%20but%20can't%20read%20words";

test("Answer: evidence label comes first, then Research says and Idea for your class", async ({
  page,
}) => {
  await fast(page);
  await page.goto(`/${ASK}`);
  const label = page.getByTestId("evidence-label");
  await expect(label).toContainText("Very sure");
  // The label is the first thing inside the answer, before any answer text.
  const first = await page.evaluate(() => {
    const l = document.querySelector('[data-testid="evidence-label"]')!;
    const p = document.querySelector("#research-says ~ p, #research-says")!.closest("section")!;
    const text = p.querySelector("p.text-lg")!;
    return !!(l.compareDocumentPosition(text) & Node.DOCUMENT_POSITION_FOLLOWING);
  });
  expect(first).toBe(true);
  await expect(page.getByRole("heading", { name: "Research says" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Idea for your class" })).toBeVisible();
  await expect(
    page
      .getByText("Example answer")
      .or(page.getByText("Example", { exact: true }))
      .first(),
  ).toBeVisible();
});

test("Answer: a numbered citation opens the sources panel with the passage and page", async ({
  page,
}) => {
  await fast(page);
  await page.goto(`/${ASK}`);
  await page
    .getByRole("button", { name: /^Source 1:/ })
    .first()
    .click();
  const dialog = page.getByRole("dialog", { name: "Sources" });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByText(/page 17/)).toBeVisible();
  await expect(dialog.locator("mark").first()).toContainText(
    "begin with words of two or three sounds",
  );
  await expectNoSeriousViolations(page);
  await expectTargets(page);
  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
  await expect(page.getByRole("button", { name: /^Source 1:/ }).first()).toBeFocused();
});

test("Loading state is calm, announced, and accessible", async ({ page }) => {
  await slow(page);
  await page.goto(`/${ASK}`);
  const status = page
    .getByRole("status")
    .filter({ hasText: "Looking through the approved research" });
  await expect(status).toBeVisible();
  await expectNoSeriousViolations(page);
  await expectTargets(page);
});

test("No-research state is honest and offers what we can help with", async ({ page }) => {
  await fast(page);
  await page.goto("/#/ask?q=How%20do%20I%20grow%20tomatoes");
  await expect(page.getByRole("heading", { name: "No research found" })).toBeVisible();
  await expect(page.getByText(/won't guess/)).toBeVisible();
  await expect(page.getByText(/phonemic awareness/)).toBeVisible();
  await expect(page.getByRole("heading", { name: "Research says" })).toHaveCount(0);
});

test("Service switched off shows a clear error with a retry", async ({ page }) => {
  await fast(page);
  await page.goto("/#/ask?q=unavailable-test");
  await expect(page.getByRole("alert")).toContainText("switched off");
  await expect(page.getByRole("button", { name: "Try again" })).toBeVisible();
  await expectNoSeriousViolations(page);
});

test("Answer: feedback buttons report their state and add to group works", async ({ page }) => {
  await fast(page);
  await page.goto(`/${ASK}`);
  const worked = page.getByRole("button", { name: "It worked" });
  await worked.click();
  await expect(worked).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByText(/Thanks\./)).toBeVisible();
  await page.getByRole("button", { name: "Add to a group's plan" }).click();
  await page.getByLabel("Which group?").selectOption({ label: "Group B" });
  await page.getByRole("button", { name: "Add", exact: true }).click();
  await expect(page.getByText(/Added to Group B/)).toBeVisible();
});
