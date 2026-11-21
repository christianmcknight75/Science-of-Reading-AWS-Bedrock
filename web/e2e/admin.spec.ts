import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page, type Route } from "@playwright/test";
import { asAdmin } from "./helpers";

const base = {
  authors: [],
  doi: null,
  url: "https://example.org/paper",
  pdf_url: null,
  license: null,
  license_snapshot_url: null,
  publisher: "Test Publisher",
  jurisdiction: "US",
  curation_status: "ready",
  curation_note: "team intends to include; awaiting Aidan's license sign-off.",
  reviewer_notes: null,
  attribution: null,
};
const sources = {
  candidate: [
    {
      ...base,
      source_id: "src_0001",
      title: "Candidate paper",
      year: 2020,
      status: "candidate",
      attribution: "\u201cCandidate paper\u201d by Test Publisher (2020).",
      reviewer_notes: "Checked against the PDF; figures on p.4 are third-party.",
    },
  ],
  approved: [
    { ...base, source_id: "src_0002", title: "Approved paper", year: 2019, status: "approved" },
  ],
  rejected: [
    { ...base, source_id: "src_0003", title: "Rejected paper", year: 2018, status: "rejected" },
  ],
};
const audit = [
  {
    ts: "2026-11-19T10:00:00Z",
    actor: "ann",
    from_status: "candidate",
    to_status: "rejected",
    reason: "Rejected: no license",
  },
];

async function mockApi(page: Page, reopened: string[] = []) {
  await asAdmin(page); // the admin page needs an admin session
  await page.route("http://localhost:8000/**", async (route: Route) => {
    const req = route.request();
    const headers = {
      "access-control-allow-origin": "*",
      "access-control-allow-headers": "*",
      "access-control-allow-methods": "GET,POST,OPTIONS",
    };
    if (req.method() === "OPTIONS") return route.fulfill({ status: 204, headers });
    const url = new URL(req.url());
    const json = (body: unknown, status = 200) =>
      route.fulfill({
        status,
        headers,
        contentType: "application/json",
        body: JSON.stringify(body),
      });
    if (url.pathname === "/admin/sources") {
      const status = (url.searchParams.get("status") ?? "candidate") as keyof typeof sources;
      return json(sources[status]);
    }
    if (url.pathname.endsWith("/audit")) return json(audit);
    if (url.pathname.endsWith("/reopen")) {
      reopened.push(JSON.parse(req.postData() ?? "{}").reason);
      return json({ ...sources.rejected[0], status: "candidate" });
    }
    return json({ detail: "not mocked" }, 404);
  });
}

async function expectNoSeriousViolations(page: Page) {
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  const bad = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
  expect(
    bad.map((v) => `${v.id} (${v.impact}): ${v.nodes.map((n) => n.target.join(" ")).join(" | ")}`),
  ).toEqual([]);
}

test("every admin call carries the bearer token", async ({ page }) => {
  const seen: (string | undefined)[] = [];
  page.on("request", (r) => {
    if (r.url().includes("/admin/sources")) seen.push(r.headers()["authorization"]);
  });
  await mockApi(page);
  await page.goto("/#/admin");
  await expect(page.getByRole("button", { name: /Candidate paper/ })).toBeVisible();
  await page.getByRole("button", { name: /Candidate paper/ }).click();
  await expect(page.getByRole("button", { name: "Approve source" })).toBeVisible();
  expect(seen.length).toBeGreaterThan(0);
  expect(seen.every((h) => h === "Bearer mock.2")).toBe(true);
});

test("waiting-for-review list and review form have no serious accessibility problems", async ({
  page,
}) => {
  await mockApi(page);
  await page.goto("/#/admin");
  await expect(page.getByRole("heading", { name: "Source review queue" })).toBeVisible();
  await expect(page.getByRole("button", { name: /Candidate paper/ })).toBeVisible();
  await expectNoSeriousViolations(page);
  await page.getByRole("button", { name: /Candidate paper/ }).click();
  await expect(page.getByRole("button", { name: "Approve source" })).toBeVisible();
  await expect(page.getByText("Curator note:")).toBeVisible();
  await expectNoSeriousViolations(page);
});

test("status tabs work with the keyboard and are announced as pressed", async ({ page }) => {
  await mockApi(page);
  await page.goto("/#/admin");
  const approved = page.getByRole("button", { name: "Approved", exact: true });
  await approved.focus();
  await page.keyboard.press("Enter");
  await expect(approved).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByRole("button", { name: /Approved paper/ })).toBeVisible();
  await expectNoSeriousViolations(page);
});

test("re-open panel needs a reason, saves it, and has no serious accessibility problems", async ({
  page,
}) => {
  const reopened: string[] = [];
  await mockApi(page, reopened);
  await page.goto("/#/admin");
  await page.getByRole("button", { name: "Rejected", exact: true }).click();
  await page.getByRole("button", { name: /Rejected paper/ }).click();
  await expect(page.getByLabel(/Reason for re-opening/)).toBeVisible();
  await expect(page.getByText("Rejected: no license")).toBeVisible(); // history
  const submit = page.getByRole("button", { name: "Re-open as candidate" });
  await expect(submit).toBeDisabled();
  await expectNoSeriousViolations(page);
  await page.getByLabel(/Reason for re-opening/).fill("Rejected by mistake");
  await expect(submit).toBeEnabled();
  await submit.click();
  await expect.poll(() => reopened).toEqual(["Rejected by mistake"]);
});

test("error message is announced and accessible", async ({ page }) => {
  await asAdmin(page);
  await page.route("http://localhost:8000/**", (route) =>
    route.fulfill({
      status: 503,
      headers: { "access-control-allow-origin": "*" },
      contentType: "application/json",
      body: JSON.stringify({ detail: "auth not configured" }),
    }),
  );
  await page.goto("/#/admin");
  await expect(page.getByRole("alert")).toContainText("auth not configured");
  await expectNoSeriousViolations(page);
});

test("every button and field is at least 48px, and keyboard focus is visible", async ({ page }) => {
  await mockApi(page);
  await page.goto("/#/admin");
  await page.getByRole("button", { name: /Candidate paper/ }).click();
  await expect(page.getByRole("button", { name: "Approve source" })).toBeVisible();
  const small = await page
    .locator(
      "button, input:not([type=checkbox]), textarea, select, label:has(input[type=checkbox])",
    )
    .evaluateAll((els) =>
      els
        .map((el) => ({
          el: (el.textContent || el.id || el.tagName).slice(0, 30),
          r: el.getBoundingClientRect(),
        }))
        .filter(({ r }) => r.height < 48 && r.height > 0)
        .map(({ el, r }) => `${el}: ${Math.round(r.height)}px high`),
    );
  expect(small).toEqual([]);

  await page.getByRole("button", { name: "Approve source" }).focus();
  const outline = await page
    .getByRole("button", { name: "Approve source" })
    .evaluate((el) => getComputedStyle(el).outlineWidth);
  expect(parseFloat(outline)).toBeGreaterThanOrEqual(2);
});

test("review form keeps the attribution and notes that were pre-filled from the curated list", async ({
  page,
}) => {
  await mockApi(page);
  await page.goto("/#/admin");
  await page.getByRole("button", { name: /Candidate paper/ }).click();
  await expect(page.getByLabel(/Attribution/)).toHaveValue(
    "\u201cCandidate paper\u201d by Test Publisher (2020).",
  );
  await expect(page.getByLabel("Reviewer notes")).toHaveValue(
    "Checked against the PDF; figures on p.4 are third-party.",
  );
});
