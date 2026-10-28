import { expect, test, type TestInfo } from "@playwright/test";

const MOCK = "MOCK - example answer, not live inference";

function uniqueAt(testInfo: TestInfo, minute: number): string {
  const shift = testInfo.project.name === "los-angeles" ? 30 : 0;
  const sec = String(10 + shift + Math.floor(Math.random() * 19)).padStart(2, "0");
  return `2026-01-16T18:0${minute}:${sec}-05:00`;
}

test("slow inference with a concurrent polling caller shows the eventual result", async ({ page }, testInfo) => {
  const pageErrors: string[] = [];
  const consoleErrors: string[] = [];
  page.on("pageerror", (error) => pageErrors.push(String(error)));
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  const at = uniqueAt(testInfo, 0);
  await page.goto(`/?e2e_at=${encodeURIComponent(at)}&e2e_delay_s=12`);
  await expect(page.locator(".banner")).toContainText("SYNTHETIC DATA", { timeout: 30_000 });
  const poller = page.evaluate(async ({ scenario, at }: { scenario: string; at: string }) => {
    const query = `?scenario=${encodeURIComponent(scenario)}&at=${encodeURIComponent(at)}`;
    const start = Date.now();
    for (;;) {
      const response = await fetch(`/api/investigations${query}`, { method: "POST" });
      if (response.status === 200) return { status: response.status, body: await response.json() };
      if (response.status !== 202) return { status: response.status, body: null };
      if (Date.now() - start > 60_000) return { status: -1, body: null };
      await new Promise((resolve) => setTimeout(resolve, 500));
    }
  }, { scenario: "demo_v1", at });
  const investigation = page.locator("section", {
    has: page.getByRole("heading", { name: "Investigation" }),
  });
  await expect(investigation.getByText(MOCK)).toBeVisible({ timeout: 60_000 });
  const result = await poller;
  expect(result.status).toBe(200);
  expect(pageErrors).toEqual([]);
  expect(consoleErrors).toEqual([]);
  await expect(page.locator("body")).not.toContainText("still pending");
});

test("server failure surfaces an unavailable explanation", async ({ page }, testInfo) => {
  const at = uniqueAt(testInfo, 1);
  await page.goto(`/?e2e_at=${encodeURIComponent(at)}&e2e_fail=1`);
  const investigation = page.locator("section", {
    has: page.getByRole("heading", { name: "Investigation" }),
  });
  await expect(investigation).toContainText("ARIA's explanation is unavailable", { timeout: 60_000 });
});

test("expired lease surfaces recovery_required distinctly", async ({ page }, testInfo) => {
  const at = uniqueAt(testInfo, 2);
  await page.goto(`/?e2e_at=${encodeURIComponent(at)}&e2e_lease_s=1&e2e_delay_s=4`);
  const outcome = page.locator("section", {
    has: page.getByRole("heading", { name: "Outcome" }),
  });
  await expect(outcome).toContainText("Inference recovery required", { timeout: 60_000 });
});

test("scenario change while pending keeps the current context", async ({ page }, testInfo) => {
  const at = uniqueAt(testInfo, 3);
  await page.goto(`/?e2e_at=${encodeURIComponent(at)}&e2e_delay_s=6`);
  await expect(page.locator(".banner")).toContainText("SYNTHETIC DATA", { timeout: 30_000 });
  await page.getByLabel("Scenario").selectOption({ label: "Trip home, thermostat offline (video)" });
  await expect(page.locator("header .eval-time")).toContainText("4:31 PM ET", { timeout: 30_000 });
  const investigation = page.locator("section", {
    has: page.getByRole("heading", { name: "Investigation" }),
  });
  await expect(investigation.getByText(MOCK)).toBeVisible({ timeout: 60_000 });
  await expect(page.getByLabel("Scenario")).toHaveValue("demo_video_v1");
  await expect(page.locator("body")).not.toContainText("Follow-up not reachable");
});

test("rapid replay changes end on the last selection with no stale overwrite", async ({ page }, testInfo) => {
  const at = uniqueAt(testInfo, 4);
  await page.goto(`/?e2e_at=${encodeURIComponent(at)}`);
  await page.getByLabel("Scenario").selectOption({ label: "Trip home, thermostat offline (video)" });
  const demoControls = page.locator(".demo-controls");
  await expect(demoControls.getByRole("button", { name: "16:31" })).toBeEnabled({ timeout: 60_000 });
  const headerTime = page.locator("header .eval-time");
  const outcome = page.locator("section", {
    has: page.getByRole("heading", { name: "Outcome" }),
  });
  await demoControls.getByRole("button", { name: "19:51" }).click();
  await demoControls.getByRole("button", { name: "20:21" }).click();
  await demoControls.getByRole("button", { name: "21:01" }).click();
  await expect(headerTime).toContainText("9:01 PM ET", { timeout: 30_000 });
  await expect(outcome.locator(".outcome-status")).toContainText("Arrival expectation met", {
    timeout: 30_000,
  });
});
