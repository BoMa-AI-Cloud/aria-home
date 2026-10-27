import { expect, test, type Locator, type Page } from "@playwright/test";

const SCENARIO = "Trip home, thermostat offline (video)";

const SECTION_IDS: Record<string, string> = {
  "Confirmed plan and permissions": "confirmed-plan-heading",
  "Simulated timeline": "timeline-heading",
  Investigation: "investigation-heading",
  "Notifications (simulated delivery)": "notifications-heading",
  Outcome: "outcome-heading",
};

function section(page: Page, heading: string) {
  return page.locator(`section[aria-labelledby="${SECTION_IDS[heading]}"]`);
}

async function show(page: Page, locator: Locator, pause = 6000) {
  await locator.evaluate((el) => el.scrollIntoView({ block: "center", inline: "center" }));
  await expect(locator).toBeVisible();
  await page.waitForTimeout(pause);
}

async function openKey(page: Page, key: string) {
  await page.goto(`http://127.0.0.1:5173/?key=${key}`);
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

async function expectCaption(page: Page, time: string) {
  await expect(page.locator(".key-caption")).toContainText(`Replay time: ${time}`);
}

async function expectOutcome(page: Page, key: string, label: string, status: string, caption: string) {
  await openKey(page, key);
  await replay(page, label);
  const outcome = section(page, "Outcome");
  await expect(outcome.locator(".outcome-status")).toContainText(`Status: ${status}`);
  await expect(outcome.locator(".latest-reading-used")).toContainText("Latest reading used:");
  await expectCaption(page, caption);
  await show(page, outcome.locator(".outcome-status"));
}

test("k-plan", async ({ page }) => {
  await openKey(page, "k-plan");
  await replay(page, "09:20");
  const plan = section(page, "Confirmed plan and permissions");
  await expect(plan).toContainText("Target temperature");
  await expect(plan).toContainText("68 F");
  await expect(plan).toContainText("Manager coordination allowed");
  await expect(plan).toContainText("Confirmed");
  await expect(plan).toContainText("9:20 AM");
  await expectCaption(page, "9:20 AM ET");
  await show(page, plan.locator(".confirmed-plan"));
});

test("k-trip", async ({ page }) => {
  await openKey(page, "k-trip");
  await replay(page, "09:20");
  const timeline = section(page, "Simulated timeline");
  const card = timeline.locator('article[aria-label="Flight confirmation email event"]');
  await expect(card).toContainText("Flight confirmation email");
  await expect(card).toContainText("SIMULATED");
  await expect(card).toContainText("Available time (received time)");
  await expectCaption(page, "9:20 AM ET");
  await show(page, card);
});

test("k-location", async ({ page }) => {
  await openKey(page, "k-location");
  await replay(page, "14:06");
  await replay(page, "16:31");
  const timeline = section(page, "Simulated timeline");
  const card = timeline.locator('article[aria-label="Location unavailable event"]');
  await expect(card).toContainText("Location unavailable");
  await expect(card).toContainText("SIMULATED");
  await expectCaption(page, "2:06 PM ET");
  await show(page, card);
});

test("k-at-risk", async ({ page }) => {
  await openKey(page, "k-at-risk");
  await replay(page, "16:31");
  const readiness = section(page, "Investigation").locator(".readiness-block");
  await expect(readiness).toContainText("Readiness: At risk. Indoor 52 F, target 68 F.");
  await expect(readiness).toContainText("thermostat telemetry missing; room sensor used");
  await expectCaption(page, "4:31 PM ET");
  await show(page, readiness);
});

test("k-help", async ({ page }) => {
  await openKey(page, "k-help");
  await replay(page, "16:52");
  const notifications = section(page, "Notifications (simulated delivery)");
  const card = notifications.locator('article[aria-label="HVAC company notification"]', {
    hasText: "Simulated delivery",
  });
  await expect(card).toHaveCount(1);
  await expect(card).toContainText("HVAC company");
  await expect(card).toContainText("Simulated delivery");
  await expect(card).toContainText("fields sent:");
  await expectCaption(page, "4:52 PM ET");
  await show(page, card);
});

test("k-ack", async ({ page }) => {
  await openKey(page, "k-ack");
  await replay(page, "16:52");
  const notifications = section(page, "Notifications (simulated delivery)");
  const card = notifications.locator('article[aria-label="Property manager notification"]');
  await card.getByRole("button", { name: "Acknowledge (simulated)" }).click();
  await expect(card).toContainText("Acknowledged, not resolved");
  await expectCaption(page, "4:52 PM ET");
  await show(page, card.locator(".notification-ack"));
});

test("k-restored", async ({ page }) => {
  await expectOutcome(page, "k-restored", "18:21", "Thermostat reporting restored", "6:21 PM ET");
});

test("k-warming", async ({ page }) => {
  await expectOutcome(page, "k-warming", "18:51", "Warming observed", "6:51 PM ET");
});

test("k-not-yet", async ({ page }) => {
  await expectOutcome(page, "k-not-yet", "19:51", "Warming observed", "7:51 PM ET");
});

test("k-verified", async ({ page }) => {
  await expectOutcome(page, "k-verified", "20:21", "Temperature goal verified", "8:21 PM ET");
});

test("k-arrival", async ({ page }) => {
  await expectOutcome(page, "k-arrival", "21:01", "Arrival expectation met", "9:01 PM ET");
});

test("k-report", async ({ page }) => {
  await openKey(page, "k-report");
  await replay(page, "20:46");
  const timeline = section(page, "Simulated timeline");
  const card = timeline.locator('article[aria-label="HVAC completion report event"]');
  await expect(card).toContainText("HVAC completion report");
  await expect(card).toContainText("Corroboration only, does not set the outcome");
  await expectCaption(page, "8:46 PM ET");
  await show(page, card);
});

test("k-home", async ({ page }) => {
  await openKey(page, "k-home");
  await replay(page, "21:01");
  const update = page.locator('article[aria-label="Homeowner update"]');
  await expect(update).toContainText("Your home reached and held 68 F before you arrived");
  await expectCaption(page, "9:01 PM ET");
  await show(page, update);
});
