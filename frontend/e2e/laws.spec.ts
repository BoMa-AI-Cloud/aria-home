import { expect, test } from "@playwright/test";

test.beforeEach(async ({ request }) => {
  const reset = await request.post("/api/e2e/reset");
  expect(reset.ok()).toBeTruthy();
});

test("ARIA's Laws view renders laws, watcher observations and corrections", async ({ page }) => {
  const failedRequests: string[] = [];
  page.on("response", (response) => {
    if (response.status() >= 400) failedRequests.push(`${response.status()} ${response.url()}`);
  });

  await page.goto("/");
  await page.getByRole("button", { name: /ARIA.*Laws/ }).first().click();

  await expect(page.getByRole("heading", { name: "ARIA’s Laws" })).toBeVisible();
  await expect(page.locator("section[aria-labelledby='laws-heading']")).toContainText("no-heat-from-watts");
  await expect(page.locator("section[aria-labelledby='laws-heading']")).toContainText("Process laws");
  await expect(page.locator("section[aria-labelledby='laws-heading']")).toContainText("Watcher observations");
  await expect(page.locator("section[aria-labelledby='laws-heading']")).toContainText("Corrections");
  await expect(page.locator("section[aria-labelledby='laws-heading']")).toContainText("never lowered by an empty watcher");

  await page.getByRole("button", { name: "Back to investigation" }).click();
  await expect(page.getByRole("heading", { name: "ARIA’s Laws" })).not.toBeVisible();

  expect(failedRequests).toEqual([]);
});
