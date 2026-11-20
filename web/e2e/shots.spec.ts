import { test, type Page } from "@playwright/test";
import { fast } from "./helpers";

// On-demand screenshots of every screen: `npm run screenshots` -> docs-screens/*.png
// (Mock mode, so the pictures show example content.) Skipped in normal test runs.
const SHOTS: { file: string; hash: string; setup?: (p: Page) => Promise<void> }[] = [
  { file: "01-home", hash: "#/" },
];

for (const s of SHOTS) {
  test(`screenshot ${s.file}`, async ({ page }) => {
    test.skip(!process.env.SHOTS, "run with npm run screenshots");
    await fast(page);
    await page.goto(`/${s.hash}`);
    await page.waitForSelector("h1");
    if (s.setup) await s.setup(page);
    await page.waitForTimeout(300);
    await page.screenshot({ path: `docs-screens/${s.file}.png`, fullPage: true });
  });
}
