import { expect, test, type Locator, type Page } from "@playwright/test";

const SCENARIO = "Winter night, older adult at home (guided story)";

test.describe("v1-arias-view", () => {
  test.use({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 2 });

  async function show(page: Page, locator: Locator, pause = 3000) {
    await locator.scrollIntoViewIfNeeded();
    await expect(locator).toBeVisible();
    await page.waitForTimeout(pause);
  }

  test("v1-arias-view", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator(".banner")).toContainText("SYNTHETIC DATA");
    await page.getByLabel("Scenario").selectOption({ label: SCENARIO });
    const controls = page.locator(".demo-controls");
    await expect(controls.getByRole("button", { name: "02:31" })).toBeEnabled();

    await controls.getByRole("button", { name: /ARIA.*view/ }).click();
    await expect(page.getByRole("heading", { name: "ARIA’s view" })).toBeVisible();
    const map = page.getByTestId("trace-map");
    await expect(map).toBeVisible();
    await show(page, map, 5000);

    const times = page.locator(".trace-times");
    for (const label of ["19:03", "02:31", "02:45", "07:01"]) {
      await times.getByRole("button", { name: label }).click();
      await expect(map).toBeVisible({ timeout: 15_000 });
      await show(page, map, 4000);
    }

    await times.getByRole("button", { name: "02:31" }).click();
    await expect(map).toBeVisible({ timeout: 15_000 });
    await page.getByTestId("trace-node-source-thermostat").click();
    await show(page, page.getByTestId("trace-detail"), 4000);

    const steps = page.locator(".trace-steps");
    await show(page, steps, 4000);
  });
});
