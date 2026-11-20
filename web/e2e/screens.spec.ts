import { expect, test } from "@playwright/test";
import {
  expectFooter,
  expectNoHorizontalScroll,
  expectNoSeriousViolations,
  expectTargets,
  fast,
} from "./helpers";

// Every screen: heading, footer, 0 serious/critical axe issues, 48px targets, no sideways scroll.
const SCREENS: { name: string; hash: string; h1: string | RegExp }[] = [
  { name: "Home", hash: "#/", h1: "What do you want to work on?" },
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
