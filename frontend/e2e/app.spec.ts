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

  expect(pageErrors).toEqual([]);
  expect(consoleErrors).toEqual([]);
  expect(failedRequests).toEqual([]);
});
