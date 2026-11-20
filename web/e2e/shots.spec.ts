import { test, type Page } from "@playwright/test";
import { fast, slow } from "./helpers";

// On-demand screenshots of every screen: `npm run screenshots` -> docs-screens/*.png
// (Mock mode, so the pictures show example content.) Skipped in normal test runs.
const ASK = "#/ask?q=My%20kids%20know%20letter%20sounds%20but%20can't%20read%20words";

interface Shot {
  file: string;
  hash: string;
  slow?: boolean;
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
];

for (const s of SHOTS) {
  test(`screenshot ${s.file}`, async ({ page }) => {
    test.skip(!process.env.SHOTS, "run with npm run screenshots");
    await (s.slow ? slow(page) : fast(page));
    await page.goto(`/${s.hash}`);
    await page.waitForSelector("h1");
    if (s.setup) await s.setup(page);
    await page.waitForTimeout(300);
    await page.screenshot({ path: `docs-screens/${s.file}.png`, fullPage: !s.setup });
  });
}
