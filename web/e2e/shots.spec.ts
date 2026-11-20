import { test, type Page } from "@playwright/test";
import { anon, asAdmin, fast, slow } from "./helpers";

// On-demand screenshots of every screen: `npm run screenshots` -> docs-screens/*.png
// (Mock mode, so the pictures show example content.) Skipped in normal test runs.
const ASK = "#/ask?q=My%20kids%20know%20letter%20sounds%20but%20can't%20read%20words";

interface Shot {
  file: string;
  hash: string;
  slow?: boolean;
  as?: "anon" | "admin";
  setup?: (p: Page) => Promise<void>;
}

const SHOTS: Shot[] = [
  { file: "01-home", hash: "#/" },
  { file: "02-answer", hash: ASK },
  {
    file: "03-answer-sources-panel",
    hash: ASK,
    setup: async (p) => {
      await p
        .getByRole("button", { name: /^Source 1:/ })
        .first()
        .click();
      await p.getByRole("dialog").waitFor();
    },
  },
  { file: "04-loading", hash: ASK, slow: true },
  { file: "05-no-research", hash: "#/ask?q=How%20do%20I%20grow%20tomatoes" },
  { file: "06-make-a-story", hash: "#/teaching/story" },
  { file: "07-tomorrows-groups", hash: "#/teaching/groups" },
  { file: "08-group-plan", hash: "#/teaching/groups/g-b" },
  { file: "13-settings", hash: "#/settings" },
  {
    file: "14-class-board",
    hash: "#/board?mode=words&title=Robot%20Talk&group=Group%20B&skill=putting%20sounds%20together&words=sat,pin,fan",
  },
  { file: "15-sign-in", hash: "#/signin", as: "anon" },
  { file: "16-request-access", hash: "#/request-access", as: "anon" },
  { file: "17-request-received", hash: "#/request-received", as: "anon" },
  { file: "18-forgot-password", hash: "#/forgot-password", as: "anon" },
  {
    file: "19-admin-access-requests",
    hash: "#/admin",
    as: "admin",
    setup: async (p) => {
      await p.getByRole("tab", { name: "Access requests" }).click();
      await p.getByText("Example Teacher One").waitFor();
    },
  },
  { file: "10-my-training", hash: "#/training" },
  { file: "11-training-topic", hash: "#/training/topic/segmenting" },
  { file: "12-refreshers", hash: "#/training/refreshers" },
  {
    file: "09-why-is-a-kid-stuck",
    hash: "#/teaching/stuck",
    setup: async (p) => {
      await p.getByRole("button", { name: "ship → sip" }).click();
      await p.getByRole("button", { name: "Find the skill" }).click();
      await p.getByText(/Skill to work on/).waitFor();
    },
  },
];

for (const s of SHOTS) {
  test(`screenshot ${s.file}`, async ({ page }) => {
    test.skip(!process.env.SHOTS, "run with npm run screenshots");
    await (s.slow
      ? slow(page)
      : s.as === "anon"
        ? anon(page)
        : s.as === "admin"
          ? asAdmin(page)
          : fast(page));
    await page.goto(`/${s.hash}`);
    await page.waitForSelector("h1");
    if (s.setup) await s.setup(page);
    await page.waitForTimeout(300);
    await page.screenshot({ path: `docs-screens/${s.file}.png`, fullPage: !s.setup });
  });
}
