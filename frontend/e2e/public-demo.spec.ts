import { expect, test, type Page } from "@playwright/test";

const FORBIDDEN_HOSTS = ["graph.facebook.com", "api.meta.ai", "emporia"];

async function isPublicDemo(page: Page): Promise<boolean> {
  try {
    const probe = await page.request.get("/api/scenarios");
    return probe.ok();
  } catch {
    return false;
  }
}

async function storyCheckpoints(page: Page): Promise<string[]> {
  const response = await page.request.get("/api/scenarios");
  expect(response.ok()).toBe(true);
  const body = await response.json();
  const story = body.scenarios.find((item: { id: string }) => item.id === "care_home_v1");
  expect(story).toBeTruthy();
  expect(story.checkpoints.length).toBeGreaterThan(0);
  return story.checkpoints as string[];
}

async function startStory(page: Page): Promise<string[]> {
  const checkpoints = await storyCheckpoints(page);
  await page.goto("/");
  await page.getByRole("button", { name: "Start the warm-by story" }).click();
  await expect(page.getByRole("heading", { name: "The warm-by story" })).toBeVisible();
  await expect(page.locator(".story-progress")).toContainText(
    `Step 1 of ${checkpoints.length}`,
  );
  return checkpoints;
}

async function stepNext(page: Page, checkpoints: string[], index: number): Promise<void> {
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await expect(page.locator(".story-progress")).toContainText(
    `Step ${index + 1} of ${checkpoints.length}`,
  );
}

test.beforeEach(async ({ page }) => {
  test.skip(!(await isPublicDemo(page)), "public-demo mode only");
});

test("landing shows purpose, disclosure and session reset", async ({ page }) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", {
      name: "Will an older adult's home be warm by morning, and if something looks wrong overnight, who should respond?",
    }),
  ).toBeVisible();
  await expect(page.locator("body")).toContainText("Petoskey");
  await expect(page.locator("body")).toContainText("in-laws");
  await expect(page.locator("body")).toContainText("Interactive demo");
  await expect(page.locator("body")).toContainText("Synthetic home data");
  await expect(page.locator("body")).toContainText("Simulated notifications");
  await expect(page.locator("body")).toContainText("No equipment control");
  await expect(page.locator("body")).toContainText("not a medical or emergency service");
  await expect(
    page.getByRole("button", { name: "Start the warm-by story" }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Explore the app freely" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Reset my session" }).first()).toBeVisible();
  await expect(page.locator('input[type="password"]')).toHaveCount(0);
  const sources = await page.request.get(
    "/api/sources?scenario=care_home_v1&at=2026-01-17T02:31:00-05:00",
  );
  expect(sources.ok()).toBe(true);
  const cookies = await page.context().cookies();
  expect(cookies.some((cookie) => cookie.name === "aria_demo_session")).toBe(true);
});

test("guided story completes from first checkpoint to warm-by time", async ({ page }) => {
  const external: string[] = [];
  page.on("request", (request) => {
    const url = request.url();
    if (FORBIDDEN_HOSTS.some((host) => url.includes(host))) external.push(url);
  });
  const checkpoints = await startStory(page);
  const story = page.locator(".story-panel");
  const outcome = page.locator("section", {
    has: page.getByRole("heading", { name: "Outcome" }),
  });
  await expect(story).toContainText("older adult lives alone");
  await stepNext(page, checkpoints, 1);
  await stepNext(page, checkpoints, 2);
  await stepNext(page, checkpoints, 3);
  await expect(outcome.locator(".outcome-status")).toContainText("Thermostat telemetry missing");
  for (let index = 4; index < checkpoints.length; index += 1) {
    await stepNext(page, checkpoints, index);
  }
  await expect(page.locator(".story-complete")).toBeVisible();
  await expect(outcome.locator(".outcome-status")).toContainText("Warm-by expectation met");
  await expect(page.locator(".story-panel")).toContainText("observed");
  await expect(page.locator(".story-panel")).toContainText("first known");
  expect(external).toEqual([]);
});

test("evidence drawer shows computed reasons and no-recording fallback", async ({
  page,
}) => {
  await startStory(page);
  await page.getByRole("button", { name: "Explore evidence" }).first().click();
  const drawer = page.locator('aside[aria-label="Explore evidence"]');
  await expect(drawer).toBeVisible();
  await expect(drawer).toContainText("Sources");
  await expect(drawer).toContainText("Readiness (computed by code)");
  await expect(drawer).toContainText("Verification (computed by code)");
  await expect(drawer).toContainText("No recorded model response for this snapshot");
  await expect(drawer).toContainText("Model contributions");
  await expect(drawer).toContainText("muse-spark-1.3");
  await expect(drawer).toContainText("sam-3.1");
  await expect(drawer).toContainText("muse-image-1.0");
  await expect(drawer).toContainText("muse-wonder-1.0");
  await expect(drawer).toContainText("fields sent:");
  await expect(drawer).not.toContainText("graph.facebook.com");
  await page.keyboard.press("Escape");
  await expect(drawer).not.toBeVisible();
});

test("ARIA's view maps the decision at a story checkpoint", async ({ page }) => {
  const checkpoints = await startStory(page);
  await stepNext(page, checkpoints, 1);
  await stepNext(page, checkpoints, 2);
  await stepNext(page, checkpoints, 3);
  await page.getByRole("button", { name: /ARIA.*view/ }).first().click();
  await expect(page.getByRole("heading", { name: "ARIA’s view" })).toBeVisible();
  await expect(page.getByTestId("trace-map")).toBeVisible();
  await expect(page.locator(".trace-steps").locator("li")).not.toHaveCount(0);
  await expect(
    page.locator('[data-testid^="trace-streak-"][data-state="fail"]').first(),
  ).toBeAttached();
  await page
    .locator("section[aria-labelledby='trace-heading']")
    .getByRole("button", { name: "Back", exact: true })
    .click();
  await expect(page.getByRole("heading", { name: "ARIA’s view" })).not.toBeVisible();
  await expect(page.getByRole("heading", { name: "The warm-by story" })).toBeVisible();
});

test("hvac fields come from the payload and ack changes no outcome", async ({ page }) => {
  const checkpoints = await startStory(page);
  const reportIndex = checkpoints.length - 1;
  for (let index = 1; index <= 4; index += 1) {
    await stepNext(page, checkpoints, index);
  }
  const story = page.locator(".story-panel");
  await expect(story).toContainText("explicitly authorizes contacting the HVAC company");
  const delivered = page.locator('article[aria-label="HVAC company notification"]', {
    hasText: "Simulated delivery",
  });
  await expect(delivered).toHaveCount(1);
  const fieldsLine = await delivered.locator(".fields-sent").innerText();
  expect(fieldsLine).toContain("property_label");
  expect(fieldsLine).toContain("access_note");
  expect(fieldsLine).toContain("manager_contact_label");
  expect(fieldsLine).toContain("relevant_observations");
  expect(await delivered.innerText()).not.toContain("itinerary");
  const outcome = page.locator("section", {
    has: page.getByRole("heading", { name: "Outcome" }),
  });
  const before = await outcome.locator(".outcome-status").innerText();
  const caregiver = page.locator('article[aria-label="Family caregiver notification"]');
  await caregiver.getByRole("button", { name: "Acknowledge (simulated)" }).click();
  await expect(caregiver).toContainText("Acknowledged, not resolved");
  await expect(outcome.locator(".outcome-status")).toContainText(before.trim());
  for (let index = 5; index <= reportIndex; index += 1) {
    await stepNext(page, checkpoints, index);
  }
  await expect(outcome.locator(".outcome-status")).toContainText("Warm-by expectation met");
});

test("two visitors are isolated and reset touches only the caller", async ({
  page,
  browser,
}) => {
  const checkpointsA = await startStory(page);
  for (let index = 1; index <= 4; index += 1) {
    await stepNext(page, checkpointsA, index);
  }
  const caregiverA = page.locator('article[aria-label="Family caregiver notification"]');
  await caregiverA.getByRole("button", { name: "Acknowledge (simulated)" }).click();
  await expect(caregiverA).toContainText("Acknowledged, not resolved");

  const contextB = await browser.newContext();
  const pageB = await contextB.newPage();
  try {
    await startStory(pageB);
    for (let index = 1; index <= 4; index += 1) {
      await stepNext(pageB, checkpointsA, index);
    }
    const caregiverB = pageB.locator('article[aria-label="Family caregiver notification"]');
    await expect(
      caregiverB.getByRole("button", { name: "Acknowledge (simulated)" }),
    ).toBeVisible();
    await expect(caregiverB).not.toContainText("Acknowledged, not resolved");

    await page.getByRole("button", { name: "Reset my session" }).first().click();
    await expect(
      page.getByRole("button", { name: "Start the warm-by story" }),
    ).toBeVisible();

    await expect(pageB.locator(".story-panel")).toBeVisible();
    await expect(caregiverB).not.toContainText("Acknowledged, not resolved");
  } finally {
    await contextB.close();
  }
});

test("rewind reveals no later state", async ({ page }) => {
  const checkpoints = await startStory(page);
  for (let index = 1; index < checkpoints.length; index += 1) {
    await stepNext(page, checkpoints, index);
  }
  await expect(page.locator("body")).toContainText("HVAC completion report");
  await page.getByRole("button", { name: "Rewind to start" }).click();
  await expect(page.locator(".story-progress")).toContainText(`Step 1 of ${checkpoints.length}`);
  const outcome = page.locator("section", {
    has: page.getByRole("heading", { name: "Outcome" }),
  });
  const timeline = page.locator("section", {
    has: page.getByRole("heading", { name: "Simulated timeline" }),
  });
  await expect(outcome.locator(".outcome-status")).not.toContainText("Warm-by expectation met");
  await expect(timeline).not.toContainText("HVAC completion report");
  await expect(page.locator("body")).not.toContainText("Acknowledged, not resolved");
});

test("rapid step changes settle on the last step", async ({ page }) => {
  const checkpoints = await startStory(page);
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await expect(page.locator(".story-progress")).toContainText(
    `Step 4 of ${checkpoints.length}`,
  );
  const outcome = page.locator("section", {
    has: page.getByRole("heading", { name: "Outcome" }),
  });
  await expect(outcome.locator(".outcome-status")).toContainText("Thermostat telemetry missing");
  await expect(outcome.locator(".outcome-status")).not.toContainText("Warm-by expectation met");
});

test("visual image is identical at UTC and offset representations", async ({ page }) => {
  const response = await page.request.get("/api/scenarios");
  const body = await response.json();
  const story = body.scenarios.find((item: { id: string }) => item.id === "care_home_v1");
  const at = (story.checkpoints as string[])[3] as string;
  const instant = new Date(at).getTime();
  const utc = new Date(instant).toISOString();
  const aheadWall = new Date(instant + (5 * 60 + 30) * 60000).toISOString().replace(/Z$/, "+05:30");
  const behindWall = new Date(instant - 8 * 3600000).toISOString().replace(/Z$/, "-08:00");
  const first = await page.request.get(
    `/api/visual/image?scenario=care_home_v1&at=${encodeURIComponent(at)}`,
  );
  const second = await page.request.get(
    `/api/visual/image?scenario=care_home_v1&at=${encodeURIComponent(utc)}`,
  );
  const third = await page.request.get(
    `/api/visual/image?scenario=care_home_v1&at=${encodeURIComponent(aheadWall)}`,
  );
  const fourth = await page.request.get(
    `/api/visual/image?scenario=care_home_v1&at=${encodeURIComponent(behindWall)}`,
  );
  expect(first.ok()).toBe(true);
  expect(second.ok()).toBe(true);
  expect(third.ok()).toBe(true);
  expect(fourth.ok()).toBe(true);
  const a = Buffer.from(await first.body());
  const b = Buffer.from(await second.body());
  const c = Buffer.from(await third.body());
  const d = Buffer.from(await fourth.body());
  expect(a.length).toBeGreaterThan(0);
  expect(a.equals(b)).toBe(true);
  expect(a.equals(c)).toBe(true);
  expect(a.equals(d)).toBe(true);
});

test("story times render in ET in any browser timezone", async ({ page }) => {
  await startStory(page);
  await expect(page.locator(".story-progress")).toContainText("ET");
  await expect(page.locator("header .eval-time")).toContainText("ET");
});

test("laptop viewport shows story and drawer", async ({ page }) => {
  await page.setViewportSize({ width: 1366, height: 768 });
  const checkpoints = await startStory(page);
  await expect(page.locator(".story-panel")).toBeVisible();
  await stepNext(page, checkpoints, 1);
  await page.getByRole("button", { name: "Explore evidence" }).first().click();
  await expect(page.locator('aside[aria-label="Explore evidence"]')).toBeVisible();
});

test("phone viewport shows landing, story and reset", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(
    page.getByRole("button", { name: "Start the warm-by story" }),
  ).toBeVisible();
  const checkpoints = await startStory(page);
  await expect(page.locator(".story-panel")).toBeVisible();
  await stepNext(page, checkpoints, 1);
  await expect(page.getByRole("button", { name: "Reset my session" }).first()).toBeVisible();
});

test("landing shows the running version", async ({ page }) => {
  const health = await (await page.request.get("/api/health")).json();
  const commit: string = health.version.commit;
  const expected = commit === "unknown" ? "Version unknown" : `Version ${commit.slice(0, 7)}`;
  await page.goto("/");
  await expect(page.getByTestId("version-line")).toHaveText(expected);
});
