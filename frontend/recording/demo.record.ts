import { expect, test, type Locator, type Page } from "@playwright/test";

const MOCK = "MOCK - example answer, not live inference";
const SCENARIO = "Trip home, thermostat offline (video)";

function section(page: Page, heading: string) {
  return page.locator("section", { has: page.getByRole("heading", { name: heading }) });
}

async function show(page: Page, locator: Locator, pause = 3000) {
  await locator.scrollIntoViewIfNeeded();
  await expect(locator).toBeVisible();
  await page.waitForTimeout(pause);
}

async function expectMockVisible(page: Page) {
  const investigation = section(page, "Investigation");
  await investigation.scrollIntoViewIfNeeded();
  await expect(investigation.getByText(MOCK)).toBeVisible();
  await page.waitForTimeout(2500);
}

async function openVideoScenario(page: Page) {
  await page.goto("http://127.0.0.1:5173/");
  await expect(page.locator(".banner")).toContainText("SYNTHETIC DATA");
  await page.getByLabel("Scenario").selectOption({ label: SCENARIO });
  const controls = page.locator(".demo-controls");
  await expect(controls.getByRole("button", { name: "16:31" })).toBeEnabled();
  await expect(section(page, "Outcome").locator(".outcome-status")).toContainText(
    "Thermostat telemetry missing",
  );
  await expectMockVisible(page);
}

async function replay(page: Page, label: string) {
  await page.locator(".demo-controls").getByRole("button", { name: label }).click();
}

test("c1-opening", async ({ page }) => {
  await page.goto("http://127.0.0.1:5173/cards.html#opening");
  await expect(
    page.getByText(
      "ARIA is my existing assistant project; its name, notes and ARIA Home designs came first. All ARIA Home code was built this week with Meta's models. Story scenes: Grok Imagine and Meta AI.",
    ),
  ).toBeVisible();
  await expect(page.getByText("Synthetic demo data")).toBeVisible();
  await page.waitForTimeout(15000);
});

test("c2-evaluation", async ({ page }) => {
  await page.goto("http://127.0.0.1:5173/cards.html#evaluation");
  await expect(page.getByText("Combined (all sources)")).toBeVisible();
  await expect(page.getByText("12/12")).toBeVisible();
  await expect(page.getByText("Thermostat only")).toBeVisible();
  await expect(page.getByText("7/12")).toBeVisible();
  await expect(page.getByText("12 builder-labelled synthetic cases. Not a benchmark of real homes.")).toBeVisible();
  await page.waitForTimeout(15000);
});

test("c3-closing", async ({ page }) => {
  await page.goto("http://127.0.0.1:5173/cards.html#closing");
  await expect(page.getByText("Not just an automation completed. An expectation met.")).toBeVisible();
  await expect(
    page.getByText(
      "ARIA Home connects the plan, coordinates the response, and verifies the result, so coming home feels like coming home.",
    ),
  ).toBeVisible();
  await expect(page.getByText("https://github.com/BoMa-AI-Cloud/aria-home")).toBeVisible();
  await page.waitForTimeout(10000);
});

test("s1-trip-cards", async ({ page }) => {
  await openVideoScenario(page);

  const timeline = section(page, "Simulated timeline");
  await replay(page, "09:20");
  for (const title of ["Flight confirmation email", "Airport location", "Confirmation request"]) {
    const card = timeline.locator("article", { hasText: title }).first();
    await expect(card).toContainText("SIMULATED");
    await expect(card).toContainText("Event time");
    await expect(card).toContainText("Available time");
    await show(page, card, 4000);
  }
  await expect(timeline.locator("article", { hasText: "Airport location" }).first()).toContainText("Consented");
  await expect(timeline.locator("article", { hasText: "Confirmation request" }).first()).toContainText("Asks");

  await replay(page, "14:06");
  for (const title of ["Preparation authorized", "Scene command", "Scene acknowledged"]) {
    const card = timeline.locator("article", { hasText: title }).first();
    await expect(card).toContainText("SIMULATED");
    await show(page, card, 4000);
  }
  const acknowledged = timeline.locator("article", { hasText: "Scene acknowledged" }).first();
  await expect(acknowledged).toContainText("Acknowledged, physical success unknown");
  await show(page, acknowledged, 6000);
  await expectMockVisible(page);
});

test("s2-not-responding", async ({ page }) => {
  await openVideoScenario(page);

  await replay(page, "16:31");
  const outcome = section(page, "Outcome");
  await expect(outcome.locator(".outcome-status")).toContainText("Thermostat telemetry missing");
  await expect(outcome).toContainText("Follow-up rule:");
  await expect(outcome).toContainText("Latest reading used: observed");
  await expect(outcome).toContainText("Evaluation (replay) time");
  await show(page, outcome.locator(".outcome-status"), 10000);

  const investigation = section(page, "Investigation");
  await expect(investigation).toContainText("Evaluation time:");
  await expect(investigation).toContainText("4:31 PM");
  await expect(investigation.getByRole("heading", { name: "Verified facts (checked against the evidence)" })).toBeVisible();
  await expect(investigation.getByRole("heading", { name: "Interpretation (model-written, not verified)" })).toBeVisible();
  await expect(investigation).toContainText("Power context");
  await expect(investigation).toContainText("Limitations:");
  await expect(investigation.getByText(MOCK)).toBeVisible();
  await show(page, investigation, 8000);
  await expectMockVisible(page);
});

test("s3-authorized-help", async ({ page }) => {
  await openVideoScenario(page);

  await replay(page, "16:31");
  const notifications = section(page, "Notifications (simulated delivery)");
  const managerCard = notifications.locator('article[aria-label="Property manager notification"]');
  await expect(managerCard).toContainText("Simulated delivery");
  await expect(managerCard).toContainText("Simulated, no message was sent");
  await show(page, managerCard, 4000);

  await replay(page, "16:52");
  const hvacCard = notifications.locator('article[aria-label="HVAC company notification"]', { hasText: "Simulated delivery" });
  await expect(hvacCard).toHaveCount(1);
  await expect(hvacCard).toContainText("fields sent:");
  await expect(hvacCard).toContainText("property_label");
  await expect(hvacCard).toContainText("access_note");
  await expect(hvacCard).toContainText("manager_contact_label");
  await expect(hvacCard).toContainText("relevant_observations");
  await expect(hvacCard).not.toContainText("itinerary");
  await show(page, hvacCard, 7000);

  const outcome = section(page, "Outcome");
  const headlineBefore = await outcome.locator(".outcome-status").innerText();
  await managerCard.scrollIntoViewIfNeeded();
  await managerCard.getByRole("button", { name: "Acknowledge (simulated)" }).click();
  await expect(managerCard).toContainText("Acknowledged, not resolved");
  await show(page, managerCard, 5000);
  await expect(outcome.locator(".outcome-status")).toContainText(headlineBefore.replace(/^Status:\s*/, ""));
  await expectMockVisible(page);
});

test("s4-recovery", async ({ page }) => {
  await openVideoScenario(page);

  const outcome = section(page, "Outcome");
  const headline = outcome.locator(".outcome-status");
  const steps: Array<[string, string]> = [
    ["18:21", "Thermostat reporting restored"],
    ["18:51", "Warming observed"],
    ["19:51", "Warming observed"],
    ["20:21", "Temperature goal verified"],
  ];
  for (const [label, expected] of steps) {
    await replay(page, label);
    await expect(headline).toContainText(expected);
    if (label === "19:51") await expect(headline).not.toContainText("Temperature goal verified");
    await expect(outcome).toContainText("Latest reading used: observed");
    await show(page, headline, label === "19:51" || label === "20:21" ? 9000 : label === "18:51" ? 7000 : 6000);
  }
  await expect(outcome.locator(".outcome-history")).toContainText("Warming observed");
  await expect(outcome.locator(".outcome-history")).toContainText("Temperature goal verified");
  await show(page, outcome.locator(".outcome-history"), 6000);
  await expectMockVisible(page);
});

test("s5-report-and-arrival", async ({ page }) => {
  await openVideoScenario(page);

  const outcome = section(page, "Outcome");
  const timeline = section(page, "Simulated timeline");
  await replay(page, "20:21");
  await expect(outcome.locator(".outcome-status")).toContainText("Temperature goal verified");
  await expect(timeline.locator("article", { hasText: "HVAC completion report" })).toHaveCount(0);

  await replay(page, "20:46");
  const report = timeline.locator("article", { hasText: "HVAC completion report" }).first();
  await expect(report).toContainText("SIMULATED");
  await expect(report).toContainText("Corroboration only, does not set the outcome");
  await show(page, report, 6000);

  await replay(page, "21:01");
  await expect(outcome.locator(".outcome-status")).toContainText("Arrival expectation met");
  await show(page, outcome.locator(".outcome-status"), 8000);
  const update = page.locator('article[aria-label="Homeowner update"]');
  await expect(update).toContainText("Your home reached and held 68 F before you arrived");
  await expect(update).toContainText("Evaluation time:");
  await show(page, update, 7000);
  await expectMockVisible(page);
});
