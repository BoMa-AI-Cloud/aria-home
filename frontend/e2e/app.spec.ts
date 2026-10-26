import { expect, test } from "@playwright/test";

const SOURCES = ["calendar", "thermostat", "electrical", "weather"];

test("synthetic evidence overview renders without errors", async ({ page }) => {
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

  await page.goto("http://127.0.0.1:5173/");

  const banner = page.locator(".banner");
  await expect(banner).toContainText("SYNTHETIC DATA");
  await expect(banner).toContainText(/synthetic/i);
  await expect(banner).not.toContainText(/live/i);

  await expect(
    page.getByRole("heading", {
      name: "Will my property be ready when I arrive, and if something looks wrong, who should respond?",
    }),
  ).toBeVisible();

  const investigation = page.locator("section", {
    has: page.getByRole("heading", { name: "Investigation" }),
  });
  const evidence = page.locator("section", {
    has: page.getByRole("heading", { name: "Evidence sources" }),
  });
  await expect(investigation).toBeVisible();
  await expect(evidence).toBeVisible();
  const investigationBox = await investigation.boundingBox();
  const evidenceBox = await evidence.boundingBox();
  expect(investigationBox).not.toBeNull();
  expect(evidenceBox).not.toBeNull();
  expect(investigationBox!.y + investigationBox!.height).toBeLessThanOrEqual(evidenceBox!.y);

  await expect(page.locator(".card")).toHaveCount(4);
  for (const source of SOURCES) {
    const card = page.locator(`article[aria-label="${source} source"]`);
    await expect(card).toHaveCount(1);
    await expect(card.getByText(/status:/i)).toBeVisible();
  }

  await expect(page.locator('article[aria-label="thermostat source"]')).toContainText(
    "Missing readings: 1",
  );
  await expect(page.locator('article[aria-label="weather source"]')).toContainText(
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
  await expect(investigation.getByRole("heading", { name: "One question for you" })).toBeVisible();
  await expect(investigation).toContainText("Who should respond first");
  await expect(investigation).toContainText("weighs against complete property power loss");
  await expect(investigation).toContainText("MOCK - example answer, not live inference");

  expect(pageErrors).toEqual([]);
  expect(consoleErrors).toEqual([]);
  expect(failedRequests).toEqual([]);
});

test("demo replay controls drive the outcome panel", async ({ page }) => {
  const failedRequests: string[] = [];
  page.on("response", (response) => {
    if (response.status() >= 400) failedRequests.push(`${response.status()} ${response.url()}`);
  });

  await page.goto("http://127.0.0.1:5173/");

  const demoControls = page.locator(".demo-controls");
  await expect(demoControls).toContainText("Demo controls");

  const outcome = page.locator("section", {
    has: page.getByRole("heading", { name: "Outcome" }),
  });
  await expect(outcome).toBeVisible();

  await page.getByLabel("Scenario").selectOption({ label: "Manager report, late warming" });
  const time1900 = demoControls.getByRole("button", { name: "19:00" });
  await expect(time1900).toBeEnabled();
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
  await expect(historyItems.first()).toBeVisible();
  expect(await historyItems.count()).toBeGreaterThanOrEqual(2);
  await expect(outcome.locator(".outcome-history")).toContainText("Warming observed");

  await page.getByLabel("Scenario").selectOption({ label: "No follow-up readings" });
  const noFollowup2031 = demoControls.getByRole("button", { name: "20:31" });
  await expect(noFollowup2031).toBeEnabled();
  await noFollowup2031.click();
  await expect(outcome.getByText("Unable to verify").first()).toBeVisible();

  expect(failedRequests).toEqual([]);
});

test("video scenario shows verification stages and simulated timeline", async ({ page }) => {
  const failedRequests: string[] = [];
  page.on("response", (response) => {
    if (response.status() >= 400) failedRequests.push(`${response.status()} ${response.url()}`);
  });

  await page.goto("http://127.0.0.1:5173/");

  const demoControls = page.locator(".demo-controls");
  const outcome = page.locator("section", {
    has: page.getByRole("heading", { name: "Outcome" }),
  });
  const timeline = page.locator("section", {
    has: page.getByRole("heading", { name: "Simulated timeline" }),
  });
  const headline = outcome.locator(".outcome-status");

  await page.getByLabel("Scenario").selectOption({ label: "Trip home, thermostat offline (video)" });

  const time1631 = demoControls.getByRole("button", { name: "16:31" });
  await expect(time1631).toBeEnabled();
  await time1631.click();
  await expect(headline).toContainText("Thermostat telemetry missing");
  await expect(outcome).toContainText("Follow-up rule:");
  await expect(outcome).toContainText("Event time");
  await expect(outcome).toContainText("Received time");
  await expect(outcome).toContainText("Evaluation (replay) time");

  const acknowledged = timeline.locator("article", { hasText: "scene_acknowledged" });
  await expect(acknowledged).toContainText("Acknowledged, physical success unknown");
  const hvacRequest = timeline.locator("article", { hasText: "hvac_request" });
  await expect(hvacRequest).toHaveCount(0);

  await demoControls.getByRole("button", { name: "18:21" }).click();
  await expect(headline).toContainText("Thermostat reporting restored");
  await expect(hvacRequest).toHaveCount(1);
  await expect(hvacRequest).toContainText("property");
  await expect(hvacRequest).toContainText("access_note");
  await expect(hvacRequest).toContainText("manager_contact");
  await expect(hvacRequest).toContainText("observations");
  await expect(hvacRequest).not.toContainText("itinerary");
  await expect(hvacRequest).not.toContainText("email");

  await demoControls.getByRole("button", { name: "19:51" }).click();
  await expect(headline).toContainText("Warming observed");
  await expect(headline).not.toContainText("Temperature goal verified");

  await demoControls.getByRole("button", { name: "20:21" }).click();
  await expect(headline).toContainText("Temperature goal verified");
  const report = timeline.locator("article", { hasText: "hvac_completion_report" });
  await expect(report).toHaveCount(0);
  await expect(timeline).not.toContainText("Corroboration only");

  await demoControls.getByRole("button", { name: "20:46" }).click();
  await expect(report).toHaveCount(1);
  await expect(report).toContainText("Corroboration only, does not set the outcome");

  await demoControls.getByRole("button", { name: "21:01" }).click();
  await expect(headline).toContainText("Arrival expectation met");

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

test("video scenario shows scoped simulated notifications and homeowner update", async ({ page }) => {
  const failedRequests: string[] = [];
  page.on("response", (response) => {
    if (response.status() >= 400) failedRequests.push(`${response.status()} ${response.url()}`);
  });

  await page.goto("http://127.0.0.1:5173/");

  const demoControls = page.locator(".demo-controls");
  const outcome = page.locator("section", {
    has: page.getByRole("heading", { name: "Outcome" }),
  });
  const notifications = page.locator("section", {
    has: page.getByRole("heading", { name: "Notifications (simulated delivery)" }),
  });
  await expect(notifications).toBeVisible();

  await page.getByLabel("Scenario").selectOption({ label: "Trip home, thermostat offline (video)" });

  const time1631 = demoControls.getByRole("button", { name: "16:31" });
  await expect(time1631).toBeEnabled();
  await time1631.click();
  await expect(outcome.locator(".outcome-status")).toContainText("Thermostat telemetry missing");

  const managerCard = notifications.locator('article[aria-label="Property manager notification"]');
  await expect(managerCard).toHaveCount(1);
  await expect(managerCard).toContainText("Property manager");
  await expect(managerCard).toContainText("Simulated delivery");
  await expect(managerCard).toContainText("Simulated, no message was sent");
  await expect(managerCard).toContainText("Created:");

  const hvacCards1631 = notifications.locator('article[aria-label="HVAC company notification"]');
  const hvacCount1631 = await hvacCards1631.count();
  if (hvacCount1631 > 0) {
    for (let i = 0; i < hvacCount1631; i += 1) {
      const text = await hvacCards1631.nth(i).innerText();
      if (!text.includes("Refused:")) throw new Error("HVAC card at 16:31 must be absent or refused");
    }
    await expect(hvacCards1631.first()).toContainText("Refused:");
  }

  await demoControls.getByRole("button", { name: "16:52" }).click();
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

  const headlineBefore = await outcome.locator(".outcome-status").innerText();
  const ackButton = managerCard.getByRole("button", { name: "Acknowledge (simulated)" });
  if ((await ackButton.count()) > 0) {
    await ackButton.click();
  }
  await expect(managerCard).toContainText("Acknowledged, not resolved");
  await expect(outcome.locator(".outcome-status")).toContainText(headlineBefore);

  await demoControls.getByRole("button", { name: "21:01" }).click();
  await expect(outcome.locator(".outcome-status")).toContainText("Arrival expectation met");
  const homeownerUpdate = page.locator('article[aria-label="Homeowner update"]');
  await expect(homeownerUpdate).toContainText("Your home reached and held 68 F before you arrived");
  await expect(homeownerUpdate).toContainText("Evaluation time:");

  const cards = notifications.locator(".notification-card");
  const cardCount = await cards.count();
  expect(cardCount).toBeGreaterThan(0);
  for (let i = 0; i < cardCount; i += 1) {
    await expect(cards.nth(i)).toContainText("Simulated");
  }

  expect(failedRequests).toEqual([]);
});
