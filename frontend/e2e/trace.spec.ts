import { expect, test, type Page } from "@playwright/test";

const CARE_SCENARIO = "Winter night, older adult at home (guided story)";
const CHECKPOINT_LABELS = [
  "7:20 PM",
  "9:00 PM",
  "9:41 PM",
  "10:46 PM",
  "11:31 PM",
  "12:21 AM",
  "12:31 AM",
  "1:41 AM",
  "1:51 AM",
  "7:01 AM",
];

test.beforeEach(async ({ request }) => {
  const reset = await request.post("/api/e2e/reset");
  expect(reset.ok()).toBeTruthy();
});

async function openTraceFromDemoControls(page: Page) {
  await page.goto("/");
  await expect(page.locator(".banner")).toContainText("SYNTHETIC DATA", { timeout: 30_000 });
  await page.getByLabel("Scenario").selectOption({ label: CARE_SCENARIO });
  const controls = page.locator(".demo-controls");
  await expect(controls.getByRole("button", { name: "11:31 PM" })).toBeEnabled();
  await controls.getByRole("button", { name: /ARIA.*view/ }).click();
  await expect(page.getByRole("heading", { name: "ARIA’s view" })).toBeVisible();
  await expect(page.getByTestId("trace-map")).toBeVisible();
}

test("ARIA's view renders the decision map at every care checkpoint", async ({ page }) => {
  test.setTimeout(90_000);
  const pageErrors: string[] = [];
  const failedTrace: string[] = [];
  page.on("pageerror", (error) => pageErrors.push(String(error)));
  page.on("response", (response) => {
    if (response.url().includes("/api/trace") && response.status() >= 400) {
      failedTrace.push(`${response.status()} ${response.url()}`);
    }
  });

  await openTraceFromDemoControls(page);
  await expect(page.locator(".trace-legend")).toContainText("violet is the model");

  for (const label of CHECKPOINT_LABELS) {
    await page.locator(".trace-times").getByRole("button", { name: label }).click();
    await expect(page.getByTestId("trace-map")).toBeVisible({ timeout: 15_000 });
    await expect(page.locator(".trace-steps").locator("li")).not.toHaveCount(0);
  }

  await page
    .locator("section[aria-labelledby='trace-heading']")
    .getByRole("button", { name: "Back to House", exact: true })
    .click();
  await expect(page.getByRole("heading", { name: "ARIA’s view" })).not.toBeVisible();

  expect(failedTrace).toEqual([]);
  expect(pageErrors).toEqual([]);
});

test("ARIA's view shows failed checks stopping at 23:31 and states changing by 07:01", async ({
  page,
}) => {
  await openTraceFromDemoControls(page);
  const section = page.locator("section[aria-labelledby='trace-heading']");
  const map = page.getByTestId("trace-map");

  await page.locator(".trace-times").getByRole("button", { name: "11:31 PM" }).click();
  await expect(map).toBeVisible({ timeout: 15_000 });
  const failedStreaks = page.locator('[data-testid^="trace-streak-"][data-state="fail"]');
  await expect(failedStreaks.first()).toBeAttached();
  const text0231 = await section.innerText();
  expect(text0231).toContain("thermostat");

  await page.getByTestId("trace-node-source-thermostat").click();
  await expect(page.getByTestId("trace-detail")).not.toContainText("Select a node or streak");

  await page.locator(".trace-times").getByRole("button", { name: "7:01 AM" }).click();
  await expect(
    page.locator(".trace-times").getByRole("button", { name: "7:01 AM" }),
  ).toHaveAttribute("aria-pressed", "true");
  await expect(map).toBeVisible({ timeout: 15_000 });
  await expect
    .poll(async () => section.innerText(), { timeout: 15_000 })
    .not.toBe(text0231);
});
