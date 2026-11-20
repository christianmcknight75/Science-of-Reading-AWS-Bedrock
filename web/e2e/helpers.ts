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

/** Mock accounts (src/api/mockAuth.ts): user 1 = demo teacher, user 2 = demo admin. */
export async function seed(page: Page, opts: { delay: number; as: "teacher" | "admin" | null }) {
  await page.addInitScript((o) => {
    (window as unknown as { __MOCK_DELAY__: number }).__MOCK_DELAY__ = o.delay;
    // Seed once per tab, not on every reload, so sign-out stays signed out.
    if (window.sessionStorage.getItem("rh-seeded")) return;
    window.sessionStorage.setItem("rh-seeded", "1");
    window.localStorage.clear();
    if (o.as) window.sessionStorage.setItem("rh-token", o.as === "admin" ? "mock.2" : "mock.1");
  }, opts);
}

/** Signed in as the demo teacher, instant mock API. */
export const fast = (page: Page) => seed(page, { delay: 0, as: "teacher" });
/** Signed in as the demo administrator. */
export const asAdmin = (page: Page) => seed(page, { delay: 0, as: "admin" });
/** Not signed in. */
export const anon = (page: Page) => seed(page, { delay: 0, as: null });
/** Signed in, and the mock API never answers: lets us look at loading states. */
export const slow = (page: Page) => seed(page, { delay: 60000, as: "teacher" });
