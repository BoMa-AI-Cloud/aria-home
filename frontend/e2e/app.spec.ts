import { expect, test } from "@playwright/test";

const SOURCES = ["calendar", "thermostat", "room_sensor", "electrical", "weather", "human_report"];

test.beforeEach(async ({ request }) => {
  const reset = await request.post("/api/e2e/reset");
  expect(reset.ok()).toBeTruthy();
});

test("synthetic evidence overview renders without errors", async ({ page }) => {
  const proxied = await page.request.get("/api/health");
  expect(proxied.ok()).toBe(true);
  const health = await proxied.json();
  const expectedDb = process.env.ARIA_HOME_E2E_DB_PATH ?? "";
  expect(health.db_marker).toBeTruthy();
  if (expectedDb) {
    expect(health.db_marker).toBe(expectedDb.split(/[\\/]/).pop());
  }
  const pageErrors: string[] = [];
  const consoleErrors: string[] = [];
  const failedRequests: string[] = [];
  page.on("pageerror", (error) => pageErrors.push(String(error)));
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("requestfailed", (request) => failedRequests.push(request.url()));
  page.on("response", (response) => {
    if (response.status() >= 400) failedRequests.push(`${response.status()} ${response.url()}`);
  });

  await page.goto("/");

  const banner = page.locator(".banner");
  await expect(banner).toContainText("SYNTHETIC DATA");
  await expect(banner).toContainText(/synthetic/i);
  await expect(banner).not.toContainText(/live/i);
  await expect(page.locator("body")).not.toContainText("Your real home, right now");

  await expect(
    page.getByRole("heading", {
      name: "Will an older adult's home be warm by morning, and if something looks wrong overnight, who should respond?",
    }),
  ).toBeVisible();

  const investigation = page.locator("section", {
    has: page.getByRole("heading", { name: "Investigation" }),
  });
  const evidence = page.locator("section", {
    has: page.getByRole("heading", { name: "Evidence sources" }),
  });
  await page.getByRole("navigation", { name: "Pages" }).getByRole("button", { name: "Reasoning" }).click();
  await expect(investigation).toBeVisible();
  await expect(evidence).toBeVisible();
  const investigationBox = await investigation.boundingBox();
  const evidenceBox = await evidence.boundingBox();
  expect(investigationBox).not.toBeNull();
  expect(evidenceBox).not.toBeNull();
  expect(investigationBox!.y + investigationBox!.height).toBeLessThanOrEqual(evidenceBox!.y);

  await page.getByRole("navigation", { name: "Pages" }).getByRole("button", { name: "House" }).click();
  const demoControls = page.locator(".demo-controls");
  const time0231 = demoControls.getByRole("button", { name: "02:31" });
  await expect(time0231).toBeEnabled({ timeout: 60_000 });
  await time0231.click();
  await expect(page.locator("header .eval-time")).toContainText("2:31 AM ET");

  await page.getByRole("navigation", { name: "Pages" }).getByRole("button", { name: "Reasoning" }).click();
  await expect(page.locator(".evidence-table tbody tr")).toHaveCount(6);
  for (const source of SOURCES) {
    const row = page.locator(`tr[data-source="${source}"]`);
    await expect(row).toHaveCount(1);
    await expect(row.getByText(/status:/i)).toBeVisible();
  }

  await expect(page.locator('tr[data-source="thermostat"]')).toContainText(
    "newest record is stale",
  );
  await expect(page.locator('tr[data-source="room_sensor"]')).toContainText(
    "52 F",
  );
  await expect(page.locator('tr[data-source="weather"]')).toContainText(
    "Forecast, not an on-property measurement",
  );

  await expect(investigation.getByText(/Readiness:/)).toContainText(
    /On track|At risk|Cannot tell/,
  );
  await expect(investigation.getByText(/Readiness:/)).toContainText(/Indoor .* target/);
  await expect(investigation.locator(".verified-facts")).toContainText("below target");
  await expect(investigation.locator(".readiness-block")).toContainText("At risk");
  await expect(
    investigation.getByRole("heading", { name: "Interpretation (model-written, not verified)" }),
  ).toBeVisible();
  await expect(investigation.locator(".interpretation")).toContainText("not verified");
  await expect(investigation.locator(".mock-label")).toContainText(/mock/i);
  await investigation.locator("summary", { hasText: "One question" }).click();
  await expect(investigation.getByRole("heading", { name: "One question for you" })).toBeVisible();
  await expect(investigation).toContainText("Who should respond first");
  await investigation.locator("summary", { hasText: "Power context" }).click();
  await expect(investigation).toContainText("weighs against complete property power loss");
  await expect(investigation).toContainText("MOCK - example answer, not live inference");
  await expect(page.locator("body")).not.toContainText("0.0342857");

  expect(pageErrors).toEqual([]);
  expect(consoleErrors).toEqual([]);
  expect(failedRequests).toEqual([]);
});

test("demo replay controls drive the outcome panel", async ({ page }) => {
  const failedRequests: string[] = [];
  page.on("response", (response) => {
    if (response.status() >= 400) failedRequests.push(`${response.status()} ${response.url()}`);
  });

  await page.goto("/");

  const demoControls = page.locator(".demo-controls");
  await expect(demoControls).toContainText("Demo controls");

  const outcome = page.locator("section", {
    has: page.getByRole("heading", { name: "Recovery so far" }),
  });
  await expect(outcome).toBeVisible();

  await page.getByLabel("Scenario").selectOption({ label: "Manager report, late warming" });
  const time1900 = demoControls.getByRole("button", { name: "19:00" });
  await expect(time1900).toBeEnabled({ timeout: 60_000 });
  await time1900.click();
  await expect(outcome.getByText("Warming observed").first()).toBeVisible();

  await demoControls.getByRole("button", { name: "20:31" }).click();
  await expect(outcome.getByText("Warming observed").first()).toBeVisible();
  await expect(outcome).toContainText(
    "An observed change after a reported action does not prove what caused it.",
  );
  await expect(outcome).toContainText(
    "Readings after the deadline are not counted toward this follow-up.",
  );
  const historyItems = outcome.locator(".outcome-history li");
  await outcome.locator("summary", { hasText: "History" }).click();
  await expect(historyItems.first()).toBeVisible();
  expect(await historyItems.count()).toBeGreaterThanOrEqual(2);
  await expect(outcome.locator(".outcome-history")).toContainText("Warming observed");

  await page.getByLabel("Scenario").selectOption({ label: "No follow-up readings" });
  const noFollowup2031 = demoControls.getByRole("button", { name: "20:31" });
  await expect(noFollowup2031).toBeEnabled({ timeout: 60_000 });
  await noFollowup2031.click();
  await expect(outcome.getByText("Unable to verify").first()).toBeVisible();

  expect(failedRequests).toEqual([]);
});

test("care scenario shows verification stages and simulated timeline", async ({ page }) => {
  const failedRequests: string[] = [];
  page.on("response", (response) => {
    if (response.status() >= 400) failedRequests.push(`${response.status()} ${response.url()}`);
  });

  await page.goto("/");

  const demoControls = page.locator(".demo-controls");
  const outcome = page.locator("section", {
    has: page.getByRole("heading", { name: "Recovery so far" }),
  });
  const timeline = page.locator("section", {
    has: page.getByRole("heading", { name: "Simulated timeline" }),
  });
  const headline = outcome.locator(".outcome-status");

  await page.getByLabel("Scenario").selectOption({ label: "Winter night, older adult at home (guided story)" });

  const time0231 = demoControls.getByRole("button", { name: "02:31" });
  await expect(time0231).toBeEnabled({ timeout: 60_000 });
  await time0231.click();
  await expect(headline).toContainText("Thermostat telemetry missing");
  await expect(outcome).toContainText("Follow-up rule:");
  await expect(outcome).toContainText("Latest reading used: observed");
  await expect(outcome).toContainText("received");
  await expect(outcome).toContainText("Evaluation (replay) time");
  const investigation = page.locator("section", {
    has: page.getByRole("heading", { name: "Investigation" }),
  });
  await page.getByRole("navigation", { name: "Pages" }).getByRole("button", { name: "Reasoning" }).click();
  await expect(investigation).toContainText("Evaluation time:");
  await expect(investigation).toContainText("2:31 AM");
  await expect(investigation).not.toContainText("06:55");
  await expect(page.locator("body")).not.toContainText("0.0342857");
  await expect(page.locator("body")).not.toContainText("None");
  await expect(page.locator("body")).not.toContainText("Email_flight_confirmation");
  await expect(page.locator("body")).toContainText("Confirmation request");
  await expect(page.locator("body")).toContainText("fields sent:");

  await page.getByRole("navigation", { name: "Pages" }).getByRole("button", { name: "House" }).click();
  await page.getByRole("navigation", { name: "Pages" }).getByRole("button", { name: "Reasoning" }).click();
  const hvacRequest = timeline.locator("article", { hasText: "HVAC request" });
  await expect(hvacRequest).toHaveCount(0);

  await page.getByRole("navigation", { name: "Pages" }).getByRole("button", { name: "House" }).click();
  await demoControls.getByRole("button", { name: "04:21" }).click();
  await expect(headline).toContainText("Thermostat reporting restored");
  await page.getByRole("navigation", { name: "Pages" }).getByRole("button", { name: "Reasoning" }).click();
  await expect(hvacRequest).toHaveCount(1);
  await expect(hvacRequest).toContainText("property");
  await expect(hvacRequest).toContainText("access_note");
  await expect(hvacRequest).toContainText("manager_contact");
  await expect(hvacRequest).toContainText("observations");
  await expect(hvacRequest).not.toContainText("itinerary");
  await expect(hvacRequest).not.toContainText("email");
  const authorized = timeline.locator("article", { hasText: "Caregiver authorized HVAC contact" });
  await expect(authorized).toHaveCount(1);

  await page.getByRole("navigation", { name: "Pages" }).getByRole("button", { name: "House" }).click();
  await demoControls.getByRole("button", { name: "04:51" }).click();
  await expect(headline).toContainText("Warming observed");
  await expect(headline).not.toContainText("Temperature goal verified");
  await expect(outcome.locator(".outcome-history")).not.toContainText("Target reached");
  await expect(outcome.locator(".outcome-history")).toContainText("Warming observed");
  await expect(outcome.locator(".outcome-history")).toContainText("4:51 AM");

  await demoControls.getByRole("button", { name: "06:21" }).click();
  await expect(headline).toContainText("Temperature goal verified");
  const evidenceTimeline = page.locator("section", {
    has: page.getByRole("heading", { name: "Evidence timeline" }),
  });
  await page.getByRole("navigation", { name: "Pages" }).getByRole("button", { name: "Reasoning" }).click();
  await expect(evidenceTimeline.locator(".evidence-timeline-entry")).toHaveCount(4);
  await expect(evidenceTimeline).not.toContainText("HVAC completion report available");
  await expect(evidenceTimeline).not.toContainText("Corroboration only");
  await page.getByRole("navigation", { name: "Pages" }).getByRole("button", { name: "House" }).click();
  await page.getByRole("navigation", { name: "Pages" }).getByRole("button", { name: "Reasoning" }).click();
  const report = timeline.locator("article", { hasText: "HVAC completion report" });
  await expect(report).toHaveCount(0);
  await expect(timeline).not.toContainText("Corroboration only");

  await page.getByRole("navigation", { name: "Pages" }).getByRole("button", { name: "House" }).click();
  await demoControls.getByRole("button", { name: "06:45" }).click();
  await page.getByRole("navigation", { name: "Pages" }).getByRole("button", { name: "Reasoning" }).click();
  await expect(report).toHaveCount(1);
  await expect(report).toContainText("Corroboration only, does not set the outcome");

  await page.getByRole("navigation", { name: "Pages" }).getByRole("button", { name: "House" }).click();
  await demoControls.getByRole("button", { name: "07:01" }).click();
  await expect(headline).toContainText("Warm-by expectation met");
  await page.getByRole("navigation", { name: "Pages" }).getByRole("button", { name: "Reasoning" }).click();
  await expect(evidenceTimeline.locator(".evidence-timeline-entry")).toHaveCount(7);
  expect(
    (await evidenceTimeline.locator(".evidence-timeline-label").allTextContents()).map((t) => t.trim()),
  ).toEqual([
    "Thermostat reporting restored",
    "Warming first observed",
    "Target first reached",
    "Hold completed and goal verified",
    "Technician voice-note report available",
    "HVAC completion report available",
    "Arrival checked",
  ]);
  const voiceNoteRow = evidenceTimeline.locator(".evidence-timeline-entry", {
    hasText: "Technician voice-note report available",
  });
  await expect(voiceNoteRow).toContainText("Corroboration only");
  await expect(voiceNoteRow).toContainText("6:40 AM ET");
  const reportRow = evidenceTimeline.locator(".evidence-timeline-entry", {
    hasText: "HVAC completion report available",
  });
  await expect(reportRow).toContainText("Corroboration only");
  await expect(reportRow).toContainText("6:45 AM ET");
  await expect(evidenceTimeline.locator(".evidence-timeline-entry").first()).toContainText("4:20 AM ET");
  await expect(evidenceTimeline.locator(".evidence-timeline-entry").last()).toContainText("7:00 AM ET");
  await page.getByRole("navigation", { name: "Pages" }).getByRole("button", { name: "House" }).click();
  await expect(outcome).toContainText("Latest reading used: observed");
  await expect(outcome.locator(".stage-times")).not.toContainText("6:40 AM");
  await expect(outcome).not.toContainText("6:40 AM");
  await expect(outcome).toContainText("7:00 AM");
  await expect(page.locator("body")).not.toContainText("0.0342857");
  await expect(page.locator("body")).not.toContainText("None");
  await expect(page.locator("body")).not.toContainText("Email_flight_confirmation");

  await page.getByRole("navigation", { name: "Pages" }).getByRole("button", { name: "Reasoning" }).click();
  const eventCards = timeline.locator(".event-card");
  const count = await eventCards.count();
  expect(count).toBeGreaterThan(0);
  for (let i = 0; i < count; i += 1) {
    await expect(eventCards.nth(i)).toContainText("SIMULATED");
    await expect(eventCards.nth(i)).toContainText("Event time");
    await expect(eventCards.nth(i)).toContainText("Available time");
  }

  expect(failedRequests).toEqual([]);
});

test("care scenario shows scoped simulated notifications and resident update", async ({ page }) => {
  const failedRequests: string[] = [];
  page.on("response", (response) => {
    if (response.status() >= 400) failedRequests.push(`${response.status()} ${response.url()}`);
  });

  await page.goto("/");

  const demoControls = page.locator(".demo-controls");
  const outcome = page.locator("section", {
    has: page.getByRole("heading", { name: "Recovery so far" }),
  });
  const notifications = page.locator("section", {
    has: page.getByRole("heading", { name: "Who knows" }),
  });
  await expect(notifications).toBeVisible();

  await page.getByLabel("Scenario").selectOption({ label: "Winter night, older adult at home (guided story)" });

  const time0231 = demoControls.getByRole("button", { name: "02:31" });
  await expect(time0231).toBeEnabled({ timeout: 60_000 });
  await time0231.click();
  await expect(outcome.locator(".outcome-status")).toContainText("Thermostat telemetry missing");

  const caregiverCard = notifications.locator('article[aria-label="Family caregiver notification"]');
  await expect(caregiverCard).toHaveCount(1);
  await expect(caregiverCard).toContainText("Family caregiver");
  await expect(caregiverCard).toContainText("Simulated delivery");
  await expect(caregiverCard).toContainText("Simulated, no message was sent");
  await expect(caregiverCard).toContainText("Created:");
  await expect(notifications.locator('article[aria-label="Property manager notification"]')).toHaveCount(0);

  const hvacCards0231 = notifications.locator('article[aria-label="HVAC company notification"]');
  const hvacCount0231 = await hvacCards0231.count();
  if (hvacCount0231 > 0) {
    for (let i = 0; i < hvacCount0231; i += 1) {
      const text = await hvacCards0231.nth(i).innerText();
      if (!text.includes("Refused:")) throw new Error("HVAC card at 02:31 must be absent or refused");
    }
    await expect(hvacCards0231.first()).toContainText("Refused:");
    await expect(hvacCards0231.first()).toContainText("caregiver has not authorized HVAC contact");
  }

  await demoControls.getByRole("button", { name: "02:45" }).click();
  const deliveredHvac = notifications.locator('article[aria-label="HVAC company notification"]', {
    hasText: "Simulated delivery",
  });
  await expect(deliveredHvac).toHaveCount(1);
  await expect(deliveredHvac).toContainText("HVAC company");
  await expect(deliveredHvac).toContainText("property_label");
  await expect(deliveredHvac).toContainText("access_note");
  await expect(deliveredHvac).toContainText("manager_contact_label");
  await expect(deliveredHvac).toContainText("relevant_observations");
  await expect(deliveredHvac).not.toContainText("itinerary");
  await expect(deliveredHvac).not.toContainText("email");
  await expect(deliveredHvac).toContainText("Simulated, no message was sent");
  await expect(deliveredHvac).toContainText("fields sent:");
  await expect(deliveredHvac).toContainText("Contact on file");
  await expect(deliveredHvac).toContainText("family caregiver on file");
  await expect(page.locator("body")).not.toContainText("None");
  await expect(page.locator("body")).not.toContainText("Email_flight_confirmation");
  const homeownerCard = notifications.locator('article[aria-label="Homeowner notification"]');
  if ((await homeownerCard.count()) > 0) {
    await expect(homeownerCard.first()).toContainText("Readiness");
    await expect(homeownerCard.first()).toContainText("Warm-by time");
    await expect(homeownerCard.first()).toContainText("fields sent:");
    await expect(homeownerCard.first()).not.toContainText("stage None");
  }

  const headlineBefore = await outcome.locator(".outcome-status").innerText();
  const ackButton = caregiverCard.getByRole("button", { name: "Acknowledge (simulated)" });
  if ((await ackButton.count()) > 0) {
    await ackButton.click();
  }
  await expect(caregiverCard).toContainText("Acknowledged, not resolved");
  await expect(outcome.locator(".outcome-status")).toContainText(headlineBefore);

  await demoControls.getByRole("button", { name: "07:01" }).click();
  await expect(outcome.locator(".outcome-status")).toContainText("Warm-by expectation met");
  const homeownerUpdate = page.locator('article[aria-label="Homeowner update"]');
  await expect(homeownerUpdate).toContainText("Your home reached and held 68 F before the warm-by time");
  await expect(homeownerUpdate).toContainText("Evaluation time:");

  const cards = notifications.locator(".notification-card");
  const cardCount = await cards.count();
  expect(cardCount).toBeGreaterThan(0);
  for (let i = 0; i < cardCount; i += 1) {
    await expect(cards.nth(i)).toContainText("Simulated");
  }

  expect(failedRequests).toEqual([]);
});

test("care scenario shows warm-by plan and consent at 19:20", async ({ page }) => {
  await page.goto("/");
  const plan = page.locator(".plan-row");
  await expect(plan).toBeVisible();
  await plan.locator("summary").click();
  await page.getByLabel("Scenario").selectOption({ label: "Winter night, older adult at home (guided story)" });
  await expect(plan).toContainText("Not yet confirmed");
  const demoControls = page.locator(".demo-controls");
  const time1920 = demoControls.getByRole("button", { name: "19:20" });
  await expect(time1920).toBeEnabled({ timeout: 60_000 });
  await time1920.click();
  await expect(plan).toContainText("demo-house");
  await expect(plan).toContainText("Warm-by time");
  await expect(plan).toContainText("7:00 AM");
  await expect(plan).not.toContainText("scenario estimates");
  await expect(plan).toContainText("68 F");
  await expect(plan).toContainText("notify homeowner");
  await expect(plan).toContainText("Caregiver coordination allowed");
  await expect(plan).toContainText("7:20 PM");
  await expect(plan).toContainText("warmby-care-001-rev1");
  await expect(plan).not.toContainText("Not yet confirmed");
});

test("without inset the full page still renders all panels", async ({ page }) => {
  await page.goto("/");
  const tabs = page.getByRole("navigation", { name: "Pages" });
  for (const heading of [
    "The house right now",
    "Who knows",
    "Recovery so far",
  ]) {
    await expect(page.getByRole("heading", { name: heading })).toBeVisible();
  }
  await expect(page.locator(".plan-row")).toBeVisible();
  await tabs.getByRole("button", { name: "Reasoning" }).click();
  for (const heading of [
    "Investigation",
    "Evidence timeline",
    "Evidence sources",
    "Simulated timeline",
  ]) {
    await expect(page.getByRole("heading", { name: heading })).toBeVisible();
  }
  await expect(page.locator(".page")).not.toHaveClass(/inset-active/);
});

test("without key the full page still renders all panels", async ({ page }) => {
  await page.goto("/");
  const tabs = page.getByRole("navigation", { name: "Pages" });
  for (const heading of [
    "The house right now",
    "Who knows",
    "Recovery so far",
  ]) {
    await expect(page.getByRole("heading", { name: heading })).toBeVisible();
  }
  await expect(page.locator(".plan-row")).toBeVisible();
  await tabs.getByRole("button", { name: "Reasoning" }).click();
  for (const heading of [
    "Investigation",
    "Evidence timeline",
    "Evidence sources",
    "Simulated timeline",
  ]) {
    await expect(page.getByRole("heading", { name: heading })).toBeVisible();
  }
  await expect(page.locator(".page")).not.toHaveClass(/key-active/);
  await expect(page.locator(".key-caption")).toHaveCount(0);
});

test("keyboard replay to 07:01 shows warm-by expectation met", async ({ page }) => {
  await page.goto("/");

  const scenario = page.getByLabel("Scenario");
  const replay0701 = page.getByRole("button", { name: "Replay to 07:01" });
  const outcome = page.locator("section", {
    has: page.getByRole("heading", { name: "Recovery so far" }),
  });

  for (let i = 0; i < 30; i += 1) {
    if (await scenario.evaluate((element) => document.activeElement === element)) break;
    await page.keyboard.press("Tab");
  }
  await expect(scenario).toBeFocused();
  await expect(scenario).toHaveValue("care_home_v1");

  await expect(replay0701).toBeEnabled({ timeout: 60_000 });
  await expect(scenario).toBeFocused();
  for (let i = 0; i < 30; i += 1) {
    if (await replay0701.evaluate((element) => document.activeElement === element)) break;
    await page.keyboard.press("Tab");
  }
  await expect(replay0701).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(outcome.locator(".outcome-status")).toContainText("Warm-by expectation met");
});

test("source cards follow scenario, replay advance and rewind in ET", async ({ page }) => {
  await page.goto("/");
  const headerTime = page.locator("header .eval-time");
  const evidence = page.locator("section", {
    has: page.getByRole("heading", { name: "Evidence sources" }),
  });
  const investigation = page.locator("section", {
    has: page.getByRole("heading", { name: "Investigation" }),
  });
  const thermostat = page.locator('tr[data-source="thermostat"]');
  await expect(headerTime).toContainText("6:00 PM ET");
  const initialCard = await thermostat.innerText();

  await page.getByLabel("Scenario").selectOption({ label: "Trip home, thermostat offline (video)" });
  await expect(headerTime).toContainText("4:31 PM ET");
  await page.getByRole("navigation", { name: "Pages" }).getByRole("button", { name: "Reasoning" }).click();
  await expect(investigation).toContainText("4:31 PM ET");
  await expect(thermostat).not.toHaveText(initialCard);

  await page.getByRole("navigation", { name: "Pages" }).getByRole("button", { name: "House" }).click();
  const demoControls = page.locator(".demo-controls");
  await demoControls.getByRole("button", { name: "18:21" }).click();
  await expect(headerTime).toContainText("6:21 PM ET");
  await page.getByRole("navigation", { name: "Pages" }).getByRole("button", { name: "Reasoning" }).click();
  await expect(investigation).toContainText(/Historical investigation/);
  const advancedCard = await thermostat.innerText();
  expect(advancedCard).not.toEqual(initialCard);

  await page.getByRole("navigation", { name: "Pages" }).getByRole("button", { name: "House" }).click();
  await demoControls.getByRole("button", { name: "16:31" }).click();
  await expect(headerTime).toContainText("4:31 PM ET");
});

test("rapid replay selections end on the last selection", async ({ page }) => {
  await page.goto("/");
  const headerTime = page.locator("header .eval-time");
  const outcome = page.locator("section", {
    has: page.getByRole("heading", { name: "Recovery so far" }),
  });
  await page.getByLabel("Scenario").selectOption({ label: "Trip home, thermostat offline (video)" });
  const demoControls = page.locator(".demo-controls");
  await expect(demoControls.getByRole("button", { name: "16:31" })).toBeEnabled({ timeout: 60_000 });
  await demoControls.getByRole("button", { name: "19:51" }).click();
  await demoControls.getByRole("button", { name: "20:21" }).click();
  await demoControls.getByRole("button", { name: "21:01" }).click();
  await expect(headerTime).toContainText("9:01 PM ET");
  await expect(outcome.locator(".outcome-status")).toContainText("Warm-by expectation met");
});

test("scenario times show ET in both browser timezones", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Scenario").selectOption({ label: "Trip home, thermostat offline (video)" });
  const investigation = page.locator("section", {
    has: page.getByRole("heading", { name: "Investigation" }),
  });
  await page.getByRole("navigation", { name: "Pages" }).getByRole("button", { name: "Reasoning" }).click();
  await expect(investigation).toContainText("4:31 PM ET");
  await expect(page.locator("header .eval-time")).toContainText("4:31 PM ET");
});

test("visual scenario shows synthetic image with segmentation overlay and verdict", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByLabel("Scenario")
    .selectOption({ label: "Water detection, low indoor temp (synthetic image)" });
  await page.getByRole("navigation", { name: "Pages" }).getByRole("button", { name: "Reasoning" }).click();
  const visual = page.locator("section", {
    has: page.getByRole("heading", { name: "Visual evidence (synthetic image)" }),
  });
  await expect(visual).toBeVisible();
  await expect(visual).toContainText(
    "Synthetic camera frame (muse-image-1.0) - segmentation by sam-3.1 (recorded)",
  );
  await expect(visual.locator("img")).toBeVisible();
  await expect(visual.locator("svg rect")).toHaveCount(1);
  await expect(visual.getByText(/Readiness:/)).toContainText("At risk");
  await expect(visual).toContainText("visual observation: water detected (synthetic image)");
});

test("care scenario shows camera frames with recorded misses", async ({ page }) => {
  const failedRequests: string[] = [];
  page.on("response", (response) => {
    if (response.status() >= 400) failedRequests.push(`${response.status()} ${response.url()}`);
  });

  await page.goto("/");
  await page.getByLabel("Scenario").selectOption({ label: "Winter night, older adult at home (guided story)" });
  const tabs = page.getByRole("navigation", { name: "Pages" });
  const visual = page.locator("section", {
    has: page.getByRole("heading", { name: "Visual evidence (synthetic image)" }),
  });
  const demoControls = page.locator(".demo-controls");

  await demoControls.getByRole("button", { name: "02:31" }).click();
  await tabs.getByRole("button", { name: "Reasoning" }).click();
  await expect(visual).toBeVisible();
  await expect(visual).toContainText(
    "Synthetic camera frame (muse-image-1.0) - segmentation by sam-3.1 (recorded)",
  );
  await expect(visual.locator("img")).toBeVisible();
  await expect(visual.locator("svg rect")).toHaveCount(0);
  await expect(visual).toContainText("Missed by the model");
  await expect(visual.getByText(/Readiness:/)).toContainText("At risk");

  await tabs.getByRole("button", { name: "House" }).click();
  await demoControls.getByRole("button", { name: "07:01" }).click();
  await tabs.getByRole("button", { name: "Reasoning" }).click();
  await expect(visual.locator("img")).toBeVisible();
  await expect(visual.locator("svg rect")).toHaveCount(0);
  await expect(visual).not.toContainText("Missed by the model");

  expect(failedRequests).toEqual([]);
});

test("footer shows the running version from /api/health", async ({ page }) => {
  const health = await (await page.request.get("/api/health")).json();
  const commit: string = health.version.commit;
  const expected = commit === "unknown" ? "Version unknown" : `Version ${commit.slice(0, 7)}`;
  await page.goto("/");
  await expect(page.getByTestId("version-line")).toHaveText(expected);
});

test("caregiver approves before ARIA contacts the HVAC company", async ({ page }) => {
  await page.goto("/");
  const demoControls = page.locator(".demo-controls");
  await page.getByLabel("Scenario").selectOption({ label: "Winter night, older adult at home (guided story)" });
  const time0231 = demoControls.getByRole("button", { name: "02:31" });
  await expect(time0231).toBeEnabled({ timeout: 60_000 });
  await time0231.click();
  const card = page.getByTestId("caregiver-permission");
  await expect(card).toContainText("your mother's home is cooling (52 F, furnace quiet since 01:30)");
  await expect(card).toContainText("Waiting for the caregiver's answer");
  const delivered = page.locator('article[aria-label="HVAC company notification"]', { hasText: "Simulated delivery" });
  await expect(delivered).toHaveCount(0);
  await card.getByRole("button", { name: "Approve (as the caregiver)" }).click();
  await expect(card).toContainText("Approved by the caregiver");
  await expect(delivered).toHaveCount(1);
  await expect(page.locator("body")).toContainText("Caregiver update: HVAC contacted");
});

test("caregiver declines and no HVAC request is made", async ({ page }) => {
  await page.goto("/");
  const demoControls = page.locator(".demo-controls");
  await page.getByLabel("Scenario").selectOption({ label: "Winter night, older adult at home (guided story)" });
  const time0231 = demoControls.getByRole("button", { name: "02:31" });
  await expect(time0231).toBeEnabled({ timeout: 60_000 });
  await time0231.click();
  const card = page.getByTestId("caregiver-permission");
  await card.getByRole("button", { name: "Decline (as the caregiver)" }).click();
  await expect(card).toContainText("Declined by the caregiver");
  await demoControls.getByRole("button", { name: "02:45" }).click();
  await expect(page.locator('article[aria-label="HVAC company notification"]', { hasText: "Simulated delivery" })).toHaveCount(0);
  await expect(page.locator("body")).toContainText("the caregiver declined HVAC contact");
});

test("live camera panel stays hidden unless the owner opts in", async ({ page }) => {
  const status = await page.request.get("/api/camera/status");
  expect((await status.json()).configured).toBe(false);
  await page.goto("/");
  await expect(page.getByTestId("version-line")).toBeVisible();
  await expect(page.getByTestId("live-camera")).toHaveCount(0);
});
