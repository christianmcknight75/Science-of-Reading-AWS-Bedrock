import AxeBuilder from "@axe-core/playwright";
import { expect, type Page } from "@playwright/test";

export async function expectNoSeriousViolations(page: Page) {
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  const bad = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
  expect(
    bad.map((v) => `${v.id} (${v.impact}): ${v.nodes.map((n) => n.target.join(" ")).join(" | ")}`),
  ).toEqual([]);
}

/** Every visible button, link and field is at least `min` px tall (48 normal, 64 classroom). */
export async function expectTargets(page: Page, min = 48) {
  const small = await page
    .locator(
      "button, a[href], input:not([type=checkbox]):not([type=radio]), select, textarea, [role=switch]",
    )
    .evaluateAll(
      (els, min) =>
        els
          .filter((el) => !el.classList.contains("skip-link"))
          .map((el) => ({
            el: (el.getAttribute("aria-label") || el.textContent || el.id || el.tagName).slice(
              0,
              40,
            ),
            r: el.getBoundingClientRect(),
          }))
          .filter(({ r }) => r.width > 0 && r.height > 0 && r.height < min - 0.5)
          .map(({ el, r }) => `${el}: ${Math.round(r.height)}px high`),
      min,
    );
  expect(small).toEqual([]);
}

export async function expectNoHorizontalScroll(page: Page) {
  const over = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(over).toBeLessThanOrEqual(0);
}

/** Footer on every screen: advisory disclaimer + content date. */
export async function expectFooter(page: Page) {
  await expect(page.getByTestId("disclaimer")).toContainText("advice only");
  await expect(page.getByText(/Content last updated:/)).toBeVisible();
}

export async function fast(page: Page) {
  await page.addInitScript(() => {
    (window as unknown as { __MOCK_DELAY__: number }).__MOCK_DELAY__ = 0;
    window.localStorage.clear();
  });
}

/** Keep the mock slow enough to look at the loading state. */
export async function slow(page: Page) {
  await page.addInitScript(() => {
    (window as unknown as { __MOCK_DELAY__: number }).__MOCK_DELAY__ = 60000;
    window.localStorage.clear();
  });
}
