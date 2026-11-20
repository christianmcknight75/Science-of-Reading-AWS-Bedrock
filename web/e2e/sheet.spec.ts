import { test } from "@playwright/test";
test("mascot sheet", async ({ page }) => {
  test.skip(!process.env.SHOTS, "on demand");
  await page.setViewportSize({ width: 820, height: 700 });
  await page.goto("/#/design");
  await page.waitForSelector('[data-testid="options"]');
  await page.getByTestId("options").screenshot({ path: "../docs/mascot/options.png" });
  await page.getByTestId("states").screenshot({ path: "../docs/mascot/states.png" });
});
