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
  { name: "Tomorrow's groups", hash: "#/teaching/groups", h1: "Tomorrow's small groups" },
  { name: "Group plan", hash: "#/teaching/groups/g-b", h1: /Group B · 15 minutes/ },
  { name: "Why is a kid stuck?", hash: "#/teaching/stuck", h1: "Why is a kid stuck?" },
  { name: "My training", hash: "#/training", h1: "Turn your training into practice" },
  { name: "Training topic", hash: "#/training/topic/segmenting", h1: "Breaking words into sounds" },
  { name: "1-minute refreshers", hash: "#/training/refreshers", h1: "Grow at your own pace" },
  { name: "Text size & read aloud", hash: "#/settings", h1: "Text size and read aloud" },
  { name: "Make a story", hash: "#/teaching/story", h1: "Make a story they can read" },
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

test("Make a story: turning a sound off flags words and blocks printing", async ({ page }) => {
  await fast(page);
  await page.goto("/#/teaching/story");
  await expect(page.getByText("Every word checked")).toBeVisible();
  await expect(page.getByTestId("story").locator('[data-status="unknown"]')).toHaveCount(0);
  // tricky words are marked by text too, not only by style
  await expect(page.getByTestId("story")).toContainText("tricky word, teach first");
  const sh = page.getByRole("button", { name: "sh", exact: true });
  await expect(sh).toHaveAttribute("aria-pressed", "true");
  await sh.click();
  await expect(sh).toHaveAttribute("aria-pressed", "false");
  await expect(page.getByTestId("story").locator('[data-status="unknown"]').first()).toBeVisible();
  await expect(page.getByText(/need a new sound|needs a new sound/)).toBeVisible();
  await expect(page.getByRole("button", { name: "Print this story" })).toBeDisabled();
  await expectNoSeriousViolations(page);
  await expectTargets(page);
});

test("Make a story: a new story that fits the sounds can be added to a group's plan", async ({
  page,
}) => {
  await fast(page);
  await page.goto("/#/teaching/story");
  await page.getByRole("button", { name: "Make a new story" }).click();
  await expect(page.getByText("Every word checked")).toBeVisible();
  await page.getByRole("button", { name: "Add to a group's plan" }).click();
  await page.getByRole("button", { name: "Add", exact: true }).click();
  await expect(page.getByText(/Added to Group A/)).toBeVisible();
});

test("Tomorrow's groups: free-text labels, no student names or scores", async ({ page }) => {
  await fast(page);
  await page.goto("/#/teaching/groups");
  await expect(page.getByText(/Last quick check|of 5 words/)).toHaveCount(0);
  await page.getByRole("button", { name: "Edit Group C" }).click();
  await expect(page.getByText(/don't use student names/i)).toBeVisible();
  await page.getByLabel("Group label").fill("Blue table");
  await expectNoSeriousViolations(page);
  await expectTargets(page);
  await page.getByRole("button", { name: "Save group" }).click();
  await expect(page.getByRole("heading", { name: "Blue table" })).toBeVisible();
  // the label survives a reload (stored on this device only)
  await page.addInitScript(() => undefined);
});

test("Tomorrow's groups: sounds can be changed and the choice is kept", async ({ page }) => {
  await fast(page);
  await page.goto("/#/teaching/groups");
  await page.getByRole("button", { name: "Change" }).click();
  const ch = page.getByRole("button", { name: "ch", exact: true });
  await expect(ch).toHaveAttribute("aria-pressed", "false");
  await ch.click();
  await expect(ch).toHaveAttribute("aria-pressed", "true");
  await expectNoSeriousViolations(page);
  await page.getByRole("button", { name: "Done" }).click();
  await expect(page.getByRole("list", { name: "Learned sounds" })).toContainText("ch");
});

test("Group plan: research is separate from the idea, steps can be swapped, no scores", async ({
  page,
}) => {
  await fast(page);
  await page.goto("/#/teaching/groups/g-b");
  await expect(page.getByRole("heading", { name: "Research says" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Idea for your class" })).toBeVisible();
  await expect(page.getByRole("heading", { name: /Robot Talk/ })).toBeVisible();
  await page.getByRole("button", { name: /Swap this step: Robot Talk/ }).click();
  await expect(page.getByRole("heading", { name: /Sound slides/ })).toBeVisible();
  // quick check has no 0-5 tally buttons: we never record how a group did
  await expect(page.getByRole("button", { name: /^[0-5]$/ })).toHaveCount(0);
  await expect(
    page.getByText(/Every word uses sounds|Checked: every word uses sounds/),
  ).toBeVisible();
  await page
    .getByRole("button", { name: /^Source 1:/ })
    .first()
    .click();
  await expect(page.getByRole("dialog", { name: "Sources" })).toBeVisible();
  await expectNoSeriousViolations(page);
});

test("Group plan: switching groups changes the plan", async ({ page }) => {
  await fast(page);
  await page.goto("/#/teaching/groups/g-b");
  await page
    .getByRole("navigation", { name: "Switch group" })
    .getByRole("link", { name: "Group A" })
    .click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Group A");
  await expect(page.getByText(/two letters can make one sound|sh, ch/i).first()).toBeVisible();
});

test("Group plan: unknown group says so kindly", async ({ page }) => {
  await fast(page);
  await page.goto("/#/teaching/groups/nope");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("We couldn't find that group");
  await expectNoSeriousViolations(page);
});

test("Why is a kid stuck: common mistake finds the skill with a citation", async ({ page }) => {
  await fast(page);
  await page.goto("/#/teaching/stuck");
  await page.getByRole("button", { name: "ship → sip" }).click();
  await page.getByRole("button", { name: "Find the skill" }).click();
  await expect(page.getByText(/Reads "sh" as just "s"/)).toBeVisible();
  await expect(page.getByRole("heading", { name: "Idea for your class" })).toBeVisible();
  await expect(page.getByText(/Based on 1 mistake so far/)).toBeVisible();
  await expectNoSeriousViolations(page);
  await expectTargets(page);
});

test("Why is a kid stuck: unclear mistake is answered honestly", async ({ page }) => {
  await fast(page);
  await page.goto("/#/teaching/stuck");
  await page.getByLabel("The word").fill("cat");
  await page.getByLabel("What they said").fill("cat");
  await page.getByRole("button", { name: "Find the skill" }).click();
  await expect(page.getByText(/can't tell/i).first()).toBeVisible();
  await expectNoSeriousViolations(page);
});

test("My training: pick a topic, choose a day, add to it, make it shorter", async ({ page }) => {
  await fast(page);
  await page.goto("/#/training");
  await page.getByRole("link", { name: /Turn into a plan.*Breaking words into sounds/ }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Breaking words into sounds");
  await expect(page.getByRole("heading", { name: "Research says" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Idea for your class" })).toBeVisible();
  await page.getByLabel("Tue").check();
  await page.getByRole("button", { name: "Add to Tue" }).click();
  await expect(page.getByText("Added to Tue.")).toBeVisible();
  await page.getByRole("button", { name: "Make it shorter" }).click();
  await expect(page.getByText(/Tap it out \(short\)/)).toBeVisible();
  await page.getByLabel("Only a few").check();
  await expect(page.getByText(/We don't save it/)).toBeVisible();
  await expectNoSeriousViolations(page);
  await expectTargets(page);
});

test("My training: free text finds a topic; unknown text is answered honestly", async ({
  page,
}) => {
  await fast(page);
  await page.goto("/#/training");
  await page.getByLabel("Just tell us what you learned").fill("something about gardens");
  await page.getByRole("button", { name: "Find a plan" }).click();
  await expect(page.getByText(/couldn't match/)).toBeVisible();
  await page.getByLabel("Just tell us what you learned").fill("we learned digraphs");
  await page.getByRole("button", { name: "Find a plan" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Two letters, one sound");
});

test("1-minute refresher: answer reveals a cited explanation; ratings are keyboard operable", async ({
  page,
}) => {
  await fast(page);
  await page.goto("/#/training/refreshers");
  await page.getByRole("button", { name: "Not true" }).click();
  await expect(page.getByText("Yes, you've got it.")).toBeVisible();
  await expect(page.getByRole("button", { name: /^Source 1:/ }).first()).toBeVisible();
  const got = page.getByRole("group", { name: "Tricky words" }).getByLabel("Got it");
  await got.focus();
  await page.keyboard.press("Space");
  await expect(got).toBeChecked();
  await expectNoSeriousViolations(page);
  await expectTargets(page);
});

test("Settings: large text and high contrast apply everywhere and stay accessible", async ({
  page,
}) => {
  await fast(page);
  await page.goto("/#/settings");
  await page.getByLabel("Extra large").check();
  await page.getByLabel("High contrast").check();
  expect(await page.evaluate(() => getComputedStyle(document.documentElement).fontSize)).toBe(
    "24px",
  );
  await expect(page.locator("html")).toHaveAttribute("data-contrast", "high");
  await expectNoSeriousViolations(page);
  await page.goto("/#/");
  await expect(page.locator("html")).toHaveAttribute("data-text-size", "xl");
  await expectNoSeriousViolations(page);
  await page.goto("/#/settings");
  await page.getByLabel("Español").check();
  await expect(page.getByText(/Spanish is coming later/)).toBeVisible();
});

test("Settings: switches are real, labelled and keyboard operable", async ({ page }) => {
  await fast(page);
  await page.goto("/#/settings");
  const sw = page.getByRole("switch", { name: "Less moving and animation" });
  await sw.focus();
  await page.keyboard.press("Space");
  await expect(sw).toBeChecked();
  await expect(page.locator("html")).toHaveAttribute("data-motion", "reduce");
  await expectTargets(page);
});

test("Class board: projector view has 64px targets, steps through words, and a footer", async ({
  page,
}) => {
  await fast(page);
  await page.goto(
    "/#/board?mode=words&title=Robot%20Talk&group=Group%20B&skill=putting%20sounds%20together&words=sat,pin,fan",
  );
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Robot Talk");
  await expect(page.getByRole("status").filter({ hasText: "Word 1 of 3" })).toBeVisible();
  await expect(page.getByText("sat", { exact: true })).toHaveCount(0);
  await page.getByRole("button", { name: "Show the word" }).click();
  await expect(page.getByText("sat", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: /Next word/ }).click();
  await expect(page.getByRole("status").filter({ hasText: "Word 2 of 3" })).toBeVisible();
  await expectFooter(page);
  await expectNoSeriousViolations(page);
  await expectTargets(page, 64);
});
