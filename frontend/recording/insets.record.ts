import { expect, test, type Locator, type Page } from "@playwright/test";

const SCENARIO = "Trip home, thermostat offline (video)";

function section(page: Page, heading: string) {
  return page.locator("section", { has: page.getByRole("heading", { name: heading }) });
}

async function show(page: Page, locator: Locator, pause = 7000) {
  await locator.evaluate((el) => el.scrollIntoView({ block: "center", inline: "center" }));
  await expect(locator).toBeVisible();
  await page.waitForTimeout(pause);
}

async function openInset(page: Page, inset: string) {
  await page.goto(`http://127.0.0.1:5173/?inset=${inset}`);
  await page.getByLabel("Scenario").selectOption({ label: SCENARIO });
  const controls = page.locator(".demo-controls");
  await expect(controls.getByRole("button", { name: "16:31" })).toBeEnabled({ timeout: 30_000 });
  await expect(page.locator(".outcome-status")).toHaveCount(1);
  await expect(page.locator(".outcome-status")).toContainText("Thermostat telemetry missing", {
    timeout: 30_000,
  });
}

async function replay(page: Page, label: string) {
  const button = page.locator(".demo-controls").getByRole("button", { name: label });
  await button.click();
  await expect(button).toBeEnabled({ timeout: 30_000 });
}

test("i0-plan", async ({ page }) => {
  await openInset(page, "plan");
  await replay(page, "09:20");
  const plan = section(page, "Confirmed plan and permissions");
  await expect(plan).toContainText("demo-cabin");
  await expect(plan).toContainText("9:00 PM");
  await expect(plan).toContainText("68 F");
  await expect(plan).toContainText("Manager coordination allowed");
  await expect(plan).toContainText("9:20 AM");
  await expect(plan).toContainText("trip-video-001-rev1");
  await expect(plan).toContainText("scenario estimates");
  await show(page, plan, 7000);
});

test("i1-trip", async ({ page }) => {
  await openInset(page, "timeline");
  await replay(page, "09:20");
  const timeline = section(page, "Simulated timeline");
  for (const title of ["Flight confirmation email", "Confirmation request"]) {
    const card = timeline.locator("article", { hasText: title }).first();
    await expect(card).toContainText("SIMULATED");
    await show(page, card, title === "Confirmation request" ? 6000 : 2500);
  }
});

test("i2-location", async ({ page }) => {
  await openInset(page, "timeline");
  await replay(page, "14:06");
  await replay(page, "16:31");
  const timeline = section(page, "Simulated timeline");
  const card = timeline.locator("article", { hasText: "Location unavailable" }).first();
  await expect(card).toContainText("SIMULATED");
  await expect(card).toContainText("Location unavailable");
  await show(page, card, 7000);
});

test("i3-not-responding", async ({ page }) => {
  await openInset(page, "not-responding");
  await replay(page, "16:31");
  const outcome = section(page, "Outcome");
  await expect(outcome.locator(".outcome-status")).toContainText("Thermostat telemetry missing");
  const readiness = section(page, "Investigation").locator(".readiness-block");
  await expect(readiness).toContainText("At risk");
  await expect(readiness).toContainText("Readiness:");
  await show(page, outcome.locator(".outcome-status"), 3500);
  await show(page, readiness, 4000);
});

test("i4-help", async ({ page }) => {
  await openInset(page, "notifications");
  await replay(page, "16:52");
  const notifications = section(page, "Notifications (simulated delivery)");
  const hvacCard = notifications.locator('article[aria-label="HVAC company notification"]', {
    hasText: "Simulated delivery",
  });
  await expect(hvacCard).toHaveCount(1);
  await expect(hvacCard).toContainText("fields sent:");
  await show(page, hvacCard, 3000);
  const managerCard = notifications.locator('article[aria-label="Property manager notification"]');
  const headlineBefore = (await page.locator(".outcome-status").textContent()) ?? "";
  await managerCard.getByRole("button", { name: "Acknowledge (simulated)" }).click();
  await expect(managerCard).toContainText("Acknowledged, not resolved");
  expect(await page.locator(".outcome-status").textContent()).toContain(
    headlineBefore.replace(/^[\s\S]*?Status:\s*/, "").trim(),
  );
  await show(page, managerCard, 4500);
});

test("i5-restored", async ({ page }) => {
  await openInset(page, "outcome");
  await replay(page, "18:21");
  const outcome = section(page, "Outcome");
  await expect(outcome.locator(".outcome-status")).toContainText("Thermostat reporting restored");
  await show(page, outcome.locator(".outcome-status"), 7000);
});

test("i6-warming", async ({ page }) => {
  await openInset(page, "outcome");
  const outcome = section(page, "Outcome");
  await replay(page, "18:51");
  await expect(outcome.locator(".outcome-status")).toContainText("Warming observed");
  await show(page, outcome.locator(".outcome-status"), 3500);
  await replay(page, "19:51");
  await expect(outcome.locator(".outcome-status")).toContainText("Warming observed");
  await expect(outcome.locator(".outcome-status")).not.toContainText("Temperature goal verified");
  await show(page, outcome.locator(".outcome-status"), 4000);
});

test("i7-verified", async ({ page }) => {
  await openInset(page, "outcome");
  await replay(page, "20:21");
  const outcome = section(page, "Outcome");
  await expect(outcome.locator(".outcome-status")).toContainText("Temperature goal verified");
  await show(page, outcome.locator(".outcome-status"), 7000);
});

test("i8-report", async ({ page }) => {
  await openInset(page, "timeline");
  await replay(page, "20:46");
  const timeline = section(page, "Simulated timeline");
  const report = timeline.locator("article", { hasText: "HVAC completion report" }).first();
  await expect(report).toContainText("SIMULATED");
  await expect(report).toContainText("Corroboration only, does not set the outcome");
  await show(page, report, 7000);
});

test("i9-arrival", async ({ page }) => {
  await openInset(page, "arrival");
  await replay(page, "21:01");
  const outcome = section(page, "Outcome");
  await expect(outcome.locator(".outcome-status")).toContainText("Arrival expectation met");
  const update = page.locator('article[aria-label="Homeowner update"]');
  await expect(update).toContainText("Your home reached and held 68 F before you arrived");
  await show(page, outcome.locator(".outcome-status"), 3500);
  await show(page, update, 4000);
});
