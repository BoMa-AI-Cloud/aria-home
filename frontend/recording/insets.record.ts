import { expect, test, type Locator, type Page } from "@playwright/test";

const SCENARIO = "Winter night, older adult at home (guided story)";

function section(page: Page, heading: string) {
  return page.locator("section", { has: page.getByRole("heading", { name: heading }) });
}

async function show(page: Page, locator: Locator, pause = 7000) {
  await locator.evaluate((el) => el.scrollIntoView({ block: "center", inline: "center" }));
  await expect(locator).toBeVisible();
  await page.waitForTimeout(pause);
}

async function openInset(page: Page, inset: string) {
  await page.goto(`/?inset=${inset}`);
  await page.getByLabel("Scenario").selectOption({ label: SCENARIO });
  const controls = page.locator(".demo-controls");
  await expect(controls.getByRole("button", { name: "19:20" })).toBeEnabled({ timeout: 30_000 });
  await expect(page.locator(".outcome-status")).toHaveCount(1);
}

async function replay(page: Page, label: string) {
  const button = page.locator(".demo-controls").getByRole("button", { name: label });
  await button.click();
  await expect(button).toBeEnabled({ timeout: 30_000 });
}

test("i0-plan", async ({ page }) => {
  await openInset(page, "plan");
  await replay(page, "19:20");
  const plan = section(page, "Confirmed plan and permissions");
  await expect(plan).toContainText("demo-house");
  await expect(plan).toContainText("Warm-by time");
  await expect(plan).toContainText("7:00 AM");
  await expect(plan).toContainText("68 F");
  await expect(plan).toContainText("Caregiver coordination allowed");
  await expect(plan).toContainText("7:20 PM");
  await expect(plan).toContainText("warmby-care-001-rev1");
  await expect(plan).not.toContainText("Not yet confirmed");
  await show(page, plan, 7000);
});

test("i1-confirm", async ({ page }) => {
  await openInset(page, "timeline");
  await replay(page, "19:20");
  const timeline = section(page, "Simulated timeline");
  const layout = await timeline.locator(".event-card").evaluateAll((cards) =>
    cards.map((card) => {
      const rect = card.getBoundingClientRect();
      const facts = card.querySelectorAll(".card-facts dt, .card-facts dd");
      return {
        top: Math.round(rect.top),
        width: rect.width,
        factsOverflow: [...facts].some((fact) => fact.scrollWidth > fact.clientWidth + 1),
      };
    }),
  );
  expect(layout.length).toBeGreaterThan(0);
  for (const card of layout) {
    expect(card.width).toBeGreaterThanOrEqual(380);
    expect(card.factsOverflow).toBe(false);
  }
  const perRow = new Map<number, number>();
  for (const card of layout) perRow.set(card.top, (perRow.get(card.top) ?? 0) + 1);
  expect(Math.max(...perRow.values())).toBeLessThanOrEqual(2);
  const card = timeline.locator("article", { hasText: "Confirmation request" }).first();
  await expect(card).toContainText("SIMULATED");
  await expect(card).toContainText("Asks");
  await show(page, card, 6000);
});

test("i2-alert", async ({ page }) => {
  await openInset(page, "timeline");
  await replay(page, "02:31");
  const timeline = section(page, "Simulated timeline");
  const card = timeline.locator("article", { hasText: "Caregiver alert" }).first();
  await expect(card).toContainText("SIMULATED");
  await expect(card).toContainText("Caregiver alert");
  await show(page, card, 7000);
});

test("i3-not-responding", async ({ page }) => {
  await openInset(page, "not-responding");
  await replay(page, "02:31");
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
  await replay(page, "02:45");
  const notifications = section(page, "Notifications (simulated delivery)");
  const hvacCard = notifications.locator('article[aria-label="HVAC company notification"]', {
    hasText: "Simulated delivery",
  });
  await expect(hvacCard).toHaveCount(1);
  await expect(hvacCard).toContainText("fields sent:");
  await expect(hvacCard).toContainText("property_label");
  await expect(hvacCard).toContainText("access_note");
  await expect(hvacCard).toContainText("relevant_observations");
  await expect(hvacCard).not.toContainText("itinerary");
  await show(page, hvacCard, 3000);
  const caregiverCard = notifications.locator('article[aria-label="Family caregiver notification"]');
  const headlineBefore = (await page.locator(".outcome-status").textContent()) ?? "";
  await caregiverCard.getByRole("button", { name: "Acknowledge (simulated)" }).click();
  await expect(caregiverCard).toContainText("Acknowledged, not resolved");
  expect(await page.locator(".outcome-status").textContent()).toContain(
    headlineBefore.replace(/^[\s\S]*?Status:\s*/, "").trim(),
  );
  await show(page, caregiverCard, 4500);
});

test("i5-restored", async ({ page }) => {
  await openInset(page, "outcome");
  await replay(page, "04:21");
  const outcome = section(page, "Outcome");
  await expect(outcome.locator(".outcome-status")).toContainText("Thermostat reporting restored");
  await show(page, outcome.locator(".outcome-status"), 7000);
});

test("i6-warming", async ({ page }) => {
  await openInset(page, "outcome");
  const outcome = section(page, "Outcome");
  await replay(page, "04:51");
  await expect(outcome.locator(".outcome-status")).toContainText("Warming observed");
  await show(page, outcome.locator(".outcome-status"), 3500);
  await replay(page, "06:21");
  await expect(outcome.locator(".outcome-status")).toContainText("Temperature goal verified");
  await show(page, outcome.locator(".outcome-status"), 4000);
});

test("i7-verified", async ({ page }) => {
  await openInset(page, "outcome");
  await replay(page, "06:21");
  const outcome = section(page, "Outcome");
  await expect(outcome.locator(".outcome-status")).toContainText("Temperature goal verified");
  await expect(outcome).toContainText("Latest reading used: observed");
  await show(page, outcome.locator(".outcome-status"), 7000);
});

test("i8-report", async ({ page }) => {
  await openInset(page, "timeline");
  await replay(page, "06:45");
  const timeline = section(page, "Simulated timeline");
  const report = timeline.locator("article", { hasText: "HVAC completion report" }).first();
  await expect(report).toContainText("SIMULATED");
  await expect(report).toContainText("Corroboration only, does not set the outcome");
  await show(page, report, 7000);
});

test("i9-warmby", async ({ page }) => {
  await openInset(page, "arrival");
  await replay(page, "07:01");
  const outcome = section(page, "Outcome");
  await expect(outcome.locator(".outcome-status")).toContainText("Warm-by expectation met");
  const update = page.locator('article[aria-label="Homeowner update"]');
  await expect(update).toContainText("Your home reached and held 68 F before the warm-by time");
  await show(page, outcome.locator(".outcome-status"), 3500);
  await show(page, update, 4000);
});

test("i10-timeline", async ({ page }) => {
  await openInset(page, "evidence-timeline");
  await replay(page, "07:01");
  const timeline = section(page, "Evidence timeline");
  await expect(timeline.locator(".evidence-timeline-entry")).toHaveCount(7);
  for (const label of [
    "Thermostat reporting restored",
    "Warming first observed",
    "Target first reached",
    "Hold completed and goal verified",
    "Technician voice-note report available",
    "HVAC completion report available",
    "Arrival checked",
  ]) {
    await expect(timeline).toContainText(label);
  }
  const report = timeline.locator(".evidence-timeline-entry", {
    hasText: "HVAC completion report available",
  });
  await expect(report).toContainText("Corroboration only");
  await show(page, timeline, 7000);
});
