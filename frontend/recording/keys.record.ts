import { expect, test, type Locator, type Page } from "@playwright/test";

const SCENARIO = "Winter night, older adult at home (guided story)";

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
  await page.goto(`/?key=${key}`);
  await page.getByLabel("Scenario").selectOption({ label: SCENARIO });
  const controls = page.locator(".demo-controls");
  await expect(controls.getByRole("button", { name: "02:31" })).toBeEnabled({ timeout: 30_000 });
  await expect(page.locator(".outcome-status")).toHaveCount(1);
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
  await replay(page, "19:20");
  const plan = section(page, "Confirmed plan and permissions");
  await expect(plan).toContainText("demo-house");
  await expect(plan).toContainText("Warm-by time");
  await expect(plan).toContainText("68 F");
  await expect(plan).toContainText("Caregiver coordination allowed");
  await expect(plan).toContainText("Confirmed");
  await expect(plan).toContainText("7:20 PM");
  await expect(plan).toContainText("warmby-care-001-rev1");
  await expectCaption(page, "7:20 PM ET");
  await show(page, plan.locator(".confirmed-plan"));
});

test("k-confirm", async ({ page }) => {
  await openKey(page, "k-confirm");
  await replay(page, "19:20");
  const timeline = section(page, "Simulated timeline");
  const card = timeline.locator("article", { hasText: "Confirmation request" }).first();
  await expect(card).toContainText("Confirmation request");
  await expect(card).toContainText("SIMULATED");
  await expect(card).toContainText("Asks");
  await expectCaption(page, "7:20 PM ET");
  await show(page, card);
});

test("k-flag", async ({ page }) => {
  await openKey(page, "k-flag");
  await replay(page, "02:31");
  const readiness = section(page, "Investigation").locator(".readiness-block");
  await expect(readiness).toContainText("Readiness:");
  await expect(readiness).toContainText("At risk");
  await expect(readiness).toContainText("52 F");
  await expectCaption(page, "2:31 AM ET");
  await show(page, readiness);
});

test("k-auth", async ({ page }) => {
  await openKey(page, "k-auth");
  await replay(page, "02:45");
  const notifications = section(page, "Notifications (simulated delivery)");
  const card = notifications.locator('article[aria-label="HVAC company notification"]', {
    hasText: "Simulated delivery",
  });
  await expect(card).toHaveCount(1);
  await expect(card).toContainText("HVAC company");
  await expect(card).toContainText("Simulated delivery");
  await expect(card).toContainText("fields sent:");
  await expectCaption(page, "2:45 AM ET");
  await show(page, card);
});

test("k-ack", async ({ page }) => {
  await openKey(page, "k-ack");
  await replay(page, "02:45");
  const notifications = section(page, "Notifications (simulated delivery)");
  const card = notifications.locator('article[aria-label="Family caregiver notification"]');
  await card.getByRole("button", { name: "Acknowledge (simulated)" }).click();
  await expect(card).toContainText("Acknowledged, not resolved");
  await expectCaption(page, "2:45 AM ET");
  await show(page, card.locator(".notification-ack"));
});

test("k-restored", async ({ page }) => {
  await expectOutcome(page, "k-restored", "04:21", "Thermostat reporting restored", "4:21 AM ET");
});

test("k-warming", async ({ page }) => {
  await expectOutcome(page, "k-warming", "04:51", "Warming observed", "4:51 AM ET");
});

test("k-verified", async ({ page }) => {
  await expectOutcome(page, "k-verified", "06:21", "Temperature goal verified", "6:21 AM ET");
});

test("k-arrival", async ({ page }) => {
  await expectOutcome(page, "k-arrival", "07:01", "Warm-by expectation met", "7:01 AM ET");
});

test("k-report", async ({ page }) => {
  await openKey(page, "k-report");
  await replay(page, "06:45");
  const timeline = section(page, "Simulated timeline");
  const card = timeline.locator("article", { hasText: "HVAC completion report" }).first();
  await expect(card).toContainText("HVAC completion report");
  await expect(card).toContainText("Corroboration only, does not set the outcome");
  await expectCaption(page, "6:45 AM ET");
  await show(page, card);
});

test("k-home", async ({ page }) => {
  await openKey(page, "k-home");
  await replay(page, "07:01");
  const update = page.locator('article[aria-label="Homeowner update"]');
  await expect(update).toContainText("before the warm-by time");
  await expectCaption(page, "7:01 AM ET");
  await show(page, update);
});
