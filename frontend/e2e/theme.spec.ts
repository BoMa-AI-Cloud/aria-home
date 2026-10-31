import { expect, test } from "@playwright/test";

test.use({ colorScheme: "dark" });

test.beforeEach(async ({ request }) => {
  const reset = await request.post("/api/e2e/reset");
  expect(reset.ok()).toBeTruthy();
});

test("demo opens in the light theme with a dark system preference", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  const background = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
  expect(background).toBe("rgb(247, 243, 236)");
  await page.getByRole("button", { name: "Switch to dark mode" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  expect(await page.evaluate(() => window.localStorage.getItem("aria-home-theme"))).toBe("dark");
  await page.getByRole("button", { name: "Switch to light mode" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  expect(await page.evaluate(() => window.localStorage.getItem("aria-home-theme"))).toBe("light");
});
