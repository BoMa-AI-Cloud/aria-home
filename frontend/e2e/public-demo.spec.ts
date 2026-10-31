import { expect, test, type Page, type Response } from "@playwright/test";

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
    has: page.getByRole("heading", { name: "Recovery so far" }),
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
  await delivered.getByText("Show the simulated message").click();
  const fieldsLine = await delivered.locator(".fields-sent").innerText();
  expect(fieldsLine).toContain("property_label");
  expect(fieldsLine).toContain("access_note");
  expect(fieldsLine).toContain("manager_contact_label");
  expect(fieldsLine).toContain("relevant_observations");
  expect(await delivered.innerText()).not.toContain("itinerary");
  const outcome = page.locator("section", {
    has: page.getByRole("heading", { name: "Recovery so far" }),
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

test("notice facts are labelled with their creation time at 02:31", async ({ page }) => {
  const checkpoints = await startStory(page);
  for (let index = 1; index <= 3; index += 1) {
    await stepNext(page, checkpoints, index);
  }
  const caregiver = page.locator('article[aria-label="Family caregiver notification"]');
  await expect(caregiver).toHaveCount(1);
  await caregiver.getByText("Show the simulated message").click();
  await expect(caregiver).toContainText("Facts when this notice was created (2:31 AM ET)");
});

test("completion report arrives after verification and ack changes no outcome", async ({ page }) => {
  const checkpoints = await startStory(page);
  const at0621 = checkpoints.findIndex((checkpoint) => checkpoint.includes("06:21"));
  expect(at0621).toBeGreaterThan(0);
  for (let index = 1; index <= 4; index += 1) {
    await stepNext(page, checkpoints, index);
  }
  const outcome = page.locator("section", {
    has: page.getByRole("heading", { name: "Recovery so far" }),
  });
  await expect.poll(async () => outcome.locator(".outcome-status").innerText()).not.toBe("");
  const before = await outcome.locator(".outcome-status").innerText();
  const caregiver = page.locator('article[aria-label="Family caregiver notification"]');
  await caregiver.getByRole("button", { name: "Acknowledge (simulated)" }).click();
  await expect(caregiver).toContainText("Acknowledged, not resolved");
  await expect(outcome.locator(".outcome-status")).toContainText(before.trim());
  for (let index = 5; index <= at0621; index += 1) {
    await stepNext(page, checkpoints, index);
  }
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
    has: page.getByRole("heading", { name: "Recovery so far" }),
  });
  const timeline = page.locator("section", {
    has: page.getByRole("heading", { name: "Simulated timeline" }),
  });
  await expect(outcome.locator(".outcome-status")).not.toContainText("Warm-by expectation met");
  await page.getByRole("navigation", { name: "Pages" }).getByRole("button", { name: "Reasoning" }).click();
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
    has: page.getByRole("heading", { name: "Recovery so far" }),
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

test("landing loads with no console errors and no failed requests", async ({ page }) => {
  const consoleErrors: string[] = [];
  const badResponses: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("response", (response) => {
    if (response.status() >= 400) badResponses.push(`${response.status()} ${response.url()}`);
  });
  await page.goto("/");
  await expect(
    page.getByRole("button", { name: "Start the warm-by story" }),
  ).toBeVisible();
  await expect(page.getByTestId("version-line")).toBeVisible();
  await page.waitForLoadState("networkidle");
  expect(consoleErrors).toEqual([]);
  expect(badResponses).toEqual([]);
});

test("guided story runs with no console errors and no failed requests", async ({ page }) => {
  const consoleErrors: string[] = [];
  const badResponses: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("response", (response) => {
    if (response.status() >= 400) badResponses.push(`${response.status()} ${response.url()}`);
  });
  const checkpoints = await startStory(page);
  for (let index = 1; index < checkpoints.length; index += 1) {
    await stepNext(page, checkpoints, index);
  }
  await expect(page.locator(".story-complete")).toBeVisible();
  await expect(
    page.locator("section", { has: page.getByRole("heading", { name: "Recovery so far" }) })
      .locator(".outcome-status"),
  ).toContainText("Warm-by expectation met");
  expect(consoleErrors).toEqual([]);
  expect(badResponses).toEqual([]);
});

test("three tabs show house, reasoning and integrations", async ({ page }) => {
  await startStory(page);
  const tabs = page.getByRole("navigation", { name: "Pages" });
  await expect(tabs.getByRole("button", { name: "House" })).toHaveAttribute("aria-current", "page");
  await expect(page.getByRole("heading", { name: "The house right now" })).toBeVisible();
  await tabs.getByRole("button", { name: "Reasoning" }).click();
  await expect(page.getByRole("heading", { name: "ARIA’s view" })).toBeVisible();
  await expect(tabs.getByRole("button", { name: "Reasoning" })).toHaveAttribute("aria-current", "page");
  await tabs.getByRole("button", { name: "Integrations" }).click();
  await expect(page.getByRole("heading", { name: "Integrations" })).toBeVisible();
  await expect(tabs.getByRole("button", { name: "Integrations" })).toHaveAttribute("aria-current", "page");
});

test("house verdict follows the replay time", async ({ page }) => {
  const checkpoints = await startStory(page);
  for (let index = 1; index <= 3; index += 1) {
    await stepNext(page, checkpoints, index);
  }
  await expect(page.locator(".verdict-headline")).toContainText("may not be warm by 7:00");
  for (let index = 4; index < checkpoints.length; index += 1) {
    await stepNext(page, checkpoints, index);
  }
  await expect(page.locator(".verdict-headline")).toContainText("expectation was met");
});

test("page has no horizontal scroll at 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 800 });
  const expectNoScroll = async () => {
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    expect(overflow).toBeLessThanOrEqual(0);
  };
  await page.goto("/");
  await expectNoScroll();
  const checkpoints = await startStory(page);
  await expectNoScroll();
  const tabs = page.getByRole("navigation", { name: "Pages" });
  await tabs.getByRole("button", { name: "Reasoning" }).click();
  await expect(page.getByRole("heading", { name: "ARIA’s view" })).toBeVisible();
  await expectNoScroll();
  await tabs.getByRole("button", { name: "Integrations" }).click();
  await expect(page.getByRole("heading", { name: "Integrations" })).toBeVisible();
  await expectNoScroll();
  await tabs.getByRole("button", { name: "House" }).click();
  for (let index = 1; index < checkpoints.length; index += 1) {
    await stepNext(page, checkpoints, index);
  }
  await expectNoScroll();
});

test("house at 02:31 has no legacy chrome and reasoning stays compact", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  const checkpoints = await startStory(page);
  for (let index = 1; index <= 3; index += 1) {
    await stepNext(page, checkpoints, index);
  }
  await expect(page.locator(".banner")).toHaveCount(0);
  await expect(page.locator("main h1")).toHaveCount(1);
  await expect(page.locator(".verdict-headline")).toBeVisible();
  const emptyHeadings = await page.evaluate(() => {
    const visible = [...document.querySelectorAll("main h1, main h2, main h3, main h4")].filter(
      (element) => {
        const rect = element.getBoundingClientRect();
        const style = getComputedStyle(element);
        return rect.width > 0 && rect.height > 0 && style.visibility !== "hidden" && style.display !== "none";
      },
    );
    return visible
      .filter((element) => (element.textContent ?? "").trim().length === 0)
      .map((element) => element.tagName);
  });
  expect(emptyHeadings).toEqual([]);
  const permission = page.getByTestId("caregiver-permission");
  await expect(permission).toContainText("52 F");
  await expect(permission).toContainText("01:30");
  await expect(permission).toContainText("No answer yet");
  await expect(permission).not.toContainText("54 F");
  await page.getByRole("navigation", { name: "Pages" }).getByRole("button", { name: "Reasoning" }).click();
  await expect(page.getByRole("heading", { name: "ARIA’s view" })).toBeVisible();
  await expect(page.getByTestId("trace-map")).toBeVisible();
  await expect(page.locator(".checks-summary")).toContainText("checks:");
  const height = await page.evaluate(
    () => Math.max(document.body.scrollHeight, document.documentElement.scrollHeight),
  );
  expect(height).toBeLessThan(4500);
});

test("reasoning at 02:31 and 07:01 and laws render with no page errors", async ({ page }) => {
  const pageErrors: string[] = [];
  const consoleErrors: string[] = [];
  page.on("pageerror", (error) => pageErrors.push(String(error)));
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  const checkpoints = await startStory(page);
  const tabs = page.getByRole("navigation", { name: "Pages" });
  const openReasoningLaws = async () => {
    await tabs.getByRole("button", { name: "Reasoning" }).click();
    await expect(page.getByRole("heading", { name: "ARIA’s view" })).toBeVisible();
    await expect(page.getByTestId("trace-map")).toBeVisible();
    await page.locator("summary", { hasText: /ARIA.*Laws/ }).first().click();
    const laws = page.locator("section[aria-labelledby='laws-heading']");
    await expect(laws).toContainText("Watcher observations");
    await expect(laws).toContainText("Corrections");
    await expect(laws).toContainText("Original:");
    await expect(page.locator("body")).not.toContainText("This section could not be shown");
  };
  const at0231 = checkpoints.findIndex((checkpoint) => checkpoint.includes("02:31"));
  expect(at0231).toBeGreaterThan(0);
  for (let index = 1; index <= at0231; index += 1) {
    await stepNext(page, checkpoints, index);
  }
  await openReasoningLaws();
  await tabs.getByRole("button", { name: "House" }).click();
  const at0701 = checkpoints.findIndex((checkpoint) => checkpoint.includes("07:01"));
  expect(at0701).toBeGreaterThan(at0231);
  for (let index = at0231 + 1; index <= at0701; index += 1) {
    await stepNext(page, checkpoints, index);
  }
  await openReasoningLaws();
  expect(pageErrors).toEqual([]);
  expect(consoleErrors).toEqual([]);
});

test("no request leaves the page origin", async ({ page }) => {
  const external: string[] = [];
  page.on("request", (request) => {
    const url = request.url();
    if (url.startsWith("data:") || url.startsWith("blob:")) return;
    if (!url.startsWith("http://127.0.0.1")) external.push(url);
  });
  const checkpoints = await startStory(page);
  await page.getByRole("navigation", { name: "Pages" }).getByRole("button", { name: "Reasoning" }).click();
  await expect(page.getByRole("heading", { name: "ARIA’s view" })).toBeVisible();
  await page.getByRole("navigation", { name: "Pages" }).getByRole("button", { name: "House" }).click();
  for (let index = 1; index < checkpoints.length; index += 1) {
    await stepNext(page, checkpoints, index);
  }
  expect(external).toEqual([]);
});

const STAGE_LABELS: Record<string, string> = {
  telemetry_missing: "Thermostat telemetry missing",
  reporting_restored: "Thermostat reporting restored",
  warming_observed: "Warming observed",
  goal_verified: "Temperature goal verified",
  goal_not_maintained: "Temperature goal no longer maintained",
  arrival_met: "Warm-by expectation met",
  unable_to_verify: "Unable to verify",
};

const READINESS_LABELS: Record<string, string> = {
  on_track: "On track",
  at_risk: "At risk",
  cannot_tell: "Cannot tell",
  arrival_passed: "Warm-by time passed",
};

const PROGRESSION = ["reporting_restored", "warming_observed", "goal_verified", "arrival_met"];
const PROGRESSION_LABELS: Record<string, string> = {
  reporting_restored: "Thermostat reporting restored",
  warming_observed: "Warming observed",
  goal_verified: "Temperature goal verified",
  arrival_met: "Warm-by expectation met",
};

type Branch = "none" | "approve" | "decline";

function pagesNav(page: Page) {
  return page.getByRole("navigation", { name: "Pages" });
}

async function toHouse(page: Page): Promise<void> {
  await pagesNav(page).getByRole("button", { name: "House" }).click();
  await expect(page.locator(".verdict-headline")).toBeVisible();
}

async function toReasoning(page: Page): Promise<void> {
  await pagesNav(page).getByRole("button", { name: "Reasoning" }).click();
  await expect(page.getByRole("heading", { name: "ARIA’s view" })).toBeVisible();
  await expect(page.getByTestId("trace-map")).toBeVisible();
}

async function runConsistencyBranch(page: Page, branch: Branch): Promise<void> {
  const createdIds: string[] = [];
  page.on("response", (response) => {
    if (response.request().method() === "POST" && response.url().includes("/api/investigations")) {
      void response
        .json()
        .then((body) => {
          if (body && typeof body.investigation_id === "string") createdIds.push(body.investigation_id);
        })
        .catch(() => {});
    }
  });
  const checkpoints = await startStory(page);
  expect(checkpoints).toHaveLength(10);
  const frozen: Array<{ text: string; requestedAt: string }> = [];

  for (let index = 0; index < checkpoints.length; index += 1) {
    if (index > 0) await stepNext(page, checkpoints, index);
    const at = checkpoints[index];
    const userDecided = branch !== "none" && index > 3;
    const scriptedApproved = index >= 4;

    await expect(page.locator(".verdict-headline")).toBeVisible();
    await expect(page.getByTestId("story-caregiver-caption")).toBeAttached();

    const metrics = await (await page.request.get(`/api/metrics?scenario=care_home_v1&at=${encodeURIComponent(at)}`)).json();
    const apiRate = metrics.indoor_trend.rate_per_hour as number | null;
    const apiSufficient = metrics.indoor_trend.sufficient as boolean;
    const apiLastValue = metrics.indoor_trend.last_value as number | null;

    const lead = page.locator(".verdict-lead");
    const insideTile = page.locator(".tiles .tile").nth(0);
    if (apiLastValue !== null) {
      await expect(lead, `lead temperature at ${at}`).toContainText(String(apiLastValue));
      await expect(insideTile.locator(".tile-value"), `inside tile at ${at}`).toContainText(String(apiLastValue));
    }
    const tileSub = insideTile.locator(".tile-sub");
    if (typeof apiRate === "number" && apiSufficient && apiRate !== 0) {
      const word = apiRate < 0 ? "falling" : "rising";
      await expect(lead, `lead trend at ${at}`).toContainText(word);
      await expect(tileSub, `tile trend at ${at}`).toContainText(word);
    } else if (typeof apiRate === "number" && apiSufficient) {
      await expect(lead, `lead trend at ${at}`).not.toContainText("falling");
      await expect(lead, `lead trend at ${at}`).not.toContainText("rising");
      await expect(tileSub, `tile trend at ${at}`).toContainText("steady");
    } else {
      await expect(lead, `lead trend at ${at}`).not.toContainText("falling");
      await expect(lead, `lead trend at ${at}`).not.toContainText("rising");
      await expect(tileSub, `tile trend at ${at}`).toContainText("trend unknown");
    }

    if (index < 2) {
      await expect(page.locator(".outcome-status strong"), `no follow-up yet at ${at}`).toHaveText(
        "No follow-up scheduled yet",
      );
      await expect(page.getByTestId("caregiver-permission"), `no permission card before the request at ${at}`).toHaveCount(0);
      await expect(page.getByTestId("story-caregiver-caption"), `caption before the request at ${at}`).toContainText(
        "No caregiver request at this step.",
      );
      const scripted = await (
        await page.request.get(`/api/trace?scenario=care_home_v1&at=${encodeURIComponent(at)}`)
      ).json();
      expect(scripted.permission, `scripted trace permission at ${at}`).toBeNull();
      continue;
    }

    let followups: any = null;
    let trace: any = null;
    await expect(async () => {
      expect(createdIds.length, `investigation created by ${at}`).toBeGreaterThan(0);
      const investigationId = createdIds[createdIds.length - 1];
      const followupsResponse = await page.request.get(
        `/api/follow-ups/${encodeURIComponent(investigationId)}?at=${encodeURIComponent(at)}`,
      );
      expect(followupsResponse.ok(), `follow-up reachable at ${at}`).toBe(true);
      const followupsBody = await followupsResponse.json();
      expect(followupsBody.status, `follow-up reached at ${at}`).not.toBe("unknown");
      const traceBody = await (
        await page.request.get(
          `/api/trace?scenario=care_home_v1&at=${encodeURIComponent(at)}&investigation_id=${encodeURIComponent(investigationId)}`,
        )
      ).json();
      followups = followupsBody;
      trace = traceBody;
    }).toPass();
    const stage = followups.verification.stage as string;
    expect(trace.verification.stage, `trace verification at ${at}`).toBe(stage);
    await expect(page.locator(".outcome-status strong"), `outcome quotes verification at ${at}`).toHaveText(
      STAGE_LABELS[stage],
    );
    const progression = await page.locator(".verification-progression li").allTextContents();
    const order = PROGRESSION.indexOf(stage);
    expect(progression, `recovery checklist at ${at}`).toEqual(
      PROGRESSION.map((item) => `${PROGRESSION_LABELS[item]} — ${order >= 0 && PROGRESSION.indexOf(item) <= order ? "Reached" : "Not reached"}`),
    );
    const verdict = (await page.locator(".verdict-headline").textContent()) ?? "";
    const leadText = (await page.locator(".verdict-lead").textContent()) ?? "";
    if (stage === "goal_verified" || stage === "arrival_met") {
      expect(verdict, `verdict never cools after recovery at ${at}`).not.toContain("cooling");
      expect(leadText, `lead never falls after recovery at ${at}`).not.toContain("falling");
      expect(verdict, `verdict celebrates recovery at ${at}`).toMatch(/verified|met/);
    }
    if (stage === "telemetry_missing") {
      const thermostatWord = (await page.locator(".tiles .tile").nth(2).locator(".tile-value").textContent()) ?? "";
      expect(thermostatWord, `thermostat tile at ${at}`).toBe("Silent");
      const gapCount = await page.locator(".gap-callout").count();
      expect(gapCount, `gap callout at ${at}`).toBeGreaterThan(0);
    }

    const permission = followups.caregiver_permission;
    const card = page.getByTestId("caregiver-permission");
    const caption = page.getByTestId("story-caregiver-caption");
    const hvacRow = page.getByTestId("know-row-hvac-company");
    if (permission === null) {
      await expect(card, `no permission card yet at ${at}`).toHaveCount(0);
      await expect(caption, `caption with no request at ${at}`).toContainText("No caregiver request at this step.");
      expect(trace.permission, `trace permission agrees at ${at}`).toBeNull();
    } else {
      await expect(card, `permission card at ${at}`).toBeVisible();
      const wantStatus =
        userDecided && branch === "approve"
          ? "approved"
          : userDecided
            ? "declined"
            : scriptedApproved
              ? "approved"
              : "waiting";
      const wantDecidedAt = userDecided ? checkpoints[3] : scriptedApproved ? checkpoints[4] : null;
      expect(permission.status, `caregiver status at ${at}`).toBe(wantStatus);
      const wantWords =
        wantStatus === "waiting"
          ? ["No answer yet", "ARIA will not contact HVAC until she answers"]
          : wantStatus === "approved"
            ? ["Approved by the caregiver at", "HVAC may now be contacted"]
            : ["Declined by the caregiver at", "No HVAC request; ARIA keeps monitoring"];
      await expect(caption, `caption at ${at}`).toContainText(wantWords[0]);
      const cardStatus = (await card.locator(".permission-status").textContent()) ?? "";
      const cardText = (await card.locator(".permission-text").textContent()) ?? "";
      const askedAt = await card.locator(".permission-asked time").getAttribute("datetime");
      expect(cardText, `frozen request text at ${at}`).toBe(permission.text);
      expect(askedAt, `asked time at ${at}`).toBe(permission.requested_at);
      frozen.push({ text: permission.text, requestedAt: permission.requested_at });
      const decidedCount = await card.locator(".permission-status time").count();
      const decidedAt = decidedCount === 0 ? null : await card.locator(".permission-status time").getAttribute("datetime");
      const hvacMeta = (await hvacRow.count()) > 0 ? ((await hvacRow.locator(".know-row-meta").textContent()) ?? "") : "";
      const captionText = (await caption.textContent()) ?? "";
      for (const words of [cardStatus, hvacMeta, captionText]) {
        expect(words, `caregiver state unmistakable at ${at}`).toContain(wantWords[0]);
        expect(words, `caregiver effect stated at ${at}`).toContain(wantWords[1]);
      }
      expect(permission.decided_at, `decision time at ${at}`).toBe(wantDecidedAt);
      expect(decidedAt, `card decision time at ${at}`).toBe(wantDecidedAt);
      expect(trace.permission, `trace permission present at ${at}`).not.toBeNull();
      expect(trace.permission.status, `trace permission agrees at ${at}`).toBe(permission.status);
      expect(trace.permission.text, `trace permission text agrees at ${at}`).toBe(permission.text);
      expect(trace.permission.requested_at, `trace permission time agrees at ${at}`).toBe(permission.requested_at);
    }
    const wantHvac = branch === "decline" ? false : branch === "approve" ? userDecided : scriptedApproved;
    if (wantHvac) {
      await expect(
        page.locator('article[aria-label="HVAC company notification"]', { hasText: "Simulated delivery" }),
        `HVAC sent after approval at ${at}`,
      ).toHaveCount(1);
    } else {
      await expect(
        page.locator('article[aria-label="HVAC company notification"]', { hasText: "Simulated delivery" }),
        `no HVAC request at ${at}`,
      ).toHaveCount(0);
    }

    await toReasoning(page);
    await expect
      .poll(async () => {
        const datetime = await page.locator(".investigation-evaluation-time time").getAttribute("datetime");
        return datetime ? Date.parse(datetime) : NaN;
      }, `reasoning answer time at ${at}`)
      .toBe(Date.parse(at));
    await expect(
      page.locator('section[aria-labelledby="investigation-heading"] .readiness-block'),
      `reasoning readiness at ${at}`,
    ).toContainText(READINESS_LABELS[metrics.computed_readiness]);
    if (followups.recorded_investigation?.status === "ok" && followups.recorded_investigation?.output) {
      const interpretation = page.locator('section[aria-labelledby="investigation-heading"] .interpretation p');
      await expect(interpretation, `current interpretation at ${at}`).toContainText(
        followups.recorded_investigation.output.interpretation.slice(0, 40),
      );
      const earlier = page.getByTestId("earlier-explanations");
      const earlierCount = await earlier.count();
      if (earlierCount > 0) {
        const earlierTimes = await earlier.locator("time").evaluateAll((nodes) =>
    nodes.map((node) => node.getAttribute("datetime")),
  );
        for (const earlierTime of earlierTimes) {
          expect(earlierTime ? Date.parse(earlierTime) : NaN, `earlier time before ${at}`).toBeLessThan(Date.parse(at));
        }
        const earlierText = (await earlier.textContent()) ?? "";
        expect(earlierText, `current answer never shown as history at ${at}`).not.toContain(
          followups.recorded_investigation.output.interpretation.slice(0, 40),
        );
      }
    } else {
      await expect(page.getByTestId("earlier-explanations"), `no history without recordings at ${at}`).toHaveCount(0);
    }
    const stepsDetails = page.locator(".trace-steps-details");
    if ((await stepsDetails.getAttribute("open")) === null) {
      await stepsDetails.locator("> summary").click();
    }
    const verificationStep = page.locator(".trace-steps li", { hasText: "verification:" });
    await expect(verificationStep, `decision map verification at ${at}`).toContainText(
      `verification: ${stage} — ${(trace.verification.reasons as string[]).join("; ")}`,
    );
    if (permission === null) {
      await expect(
        page.locator(".trace-steps li", { hasText: "caregiver permission" }),
        `no permission step at ${at}`,
      ).toHaveCount(0);
    } else {
      await expect(
        page.locator(".trace-steps li", { hasText: "caregiver permission" }),
        `decision map permission text at ${at}`,
      ).toContainText(permission.text);
    }

    if (branch !== "none" && index === 3) {
      await toHouse(page);
      const action = branch === "approve" ? "Approve (as the caregiver)" : "Decline (as the caregiver)";
      await card.getByRole("button", { name: action }).click();
      const want = branch === "approve" ? "Approved by the caregiver at" : "Declined by the caregiver at";
      await expect(card.locator(".permission-status")).toContainText(want);
      continue;
    }
    await toHouse(page);
  }

  expect(frozen.length, "frozen request seen").toBeGreaterThan(0);
  for (const entry of frozen) {
    expect(entry.text, "request text frozen").toBe(frozen[0].text);
    expect(entry.requestedAt, "request time frozen").toBe(frozen[0].requestedAt);
  }
}

test("guided story never contradicts itself with no caregiver decision", async ({ page }) => {
  await runConsistencyBranch(page, "none");
});

test("guided story never contradicts itself when the caregiver approves at 02:31", async ({ page }) => {
  await runConsistencyBranch(page, "approve");
});

test("guided story never contradicts itself when the caregiver declines at 02:31", async ({ page }) => {
  await runConsistencyBranch(page, "decline");
});

test("earlier explanations list earlier recorded answers, never as the current one", async ({ page }) => {
  function isRecordResponse(at: string): (response: Response) => boolean {
    const encoded = `at=${encodeURIComponent(at)}`;
    return (response: Response): boolean => {
      const url = response.url();
      if (!url.includes(encoded)) return false;
      if (response.request().method() === "POST" && url.includes("/api/investigations")) return true;
      return url.includes("/api/follow-ups/");
    };
  }
  async function settleRecord(pending: Promise<Response>): Promise<void> {
    // Story progress updates synchronously on click, but the record-bearing
    // responses (POST /api/investigations or GET /api/follow-ups) resolve
    // later and token guards drop them once the next step starts. The drain
    // lets the surviving continuation store the record before moving on.
    await pending;
    await page.waitForTimeout(250);
  }
  function injectedOutput(at: string): Record<string, unknown> {
    return {
      facts: [],
      verified_facts: [],
      interpretation: `injected interpretation for ${at}`,
      hypotheses: [],
      unknowns: [],
      clarification: "No question.",
      follow_up: {
        observation: "Keep watching.",
        when: null,
        next_check_at: null,
        schedule_status: "",
        deadline_passed: false,
      },
      readiness: "at_risk",
      limitations: [],
    };
  }
  async function injectRecorded(route: import("@playwright/test").Route): Promise<void> {
    const response = await route.fetch();
    const body = await response.json();
    const at = new URL(route.request().url()).searchParams.get("at") ?? "unknown";
    if (route.request().method() === "POST") {
      if (body.investigation) {
        body.investigation.status = "ok";
        body.investigation.model_id = "muse-spark-1.3";
        body.investigation.provider_mode = "recorded";
        body.investigation.output = injectedOutput(at);
      }
    } else {
      const recorded = body.recorded_investigation ?? {};
      body.recorded_investigation = {
        ...recorded,
        status: "ok",
        output: injectedOutput(at),
        reasons: [],
        model_id: "muse-spark-1.3",
        provider_mode: "recorded",
      };
    }
    await route.fulfill({ response, json: body });
  }
  await page.route("**/api/follow-ups/*", injectRecorded);
  await page.route("**/api/investigations*", injectRecorded);
  const checkpoints = await storyCheckpoints(page);
  await page.goto("/");
  await page.waitForResponse(
    (response) => response.request().method() === "POST" && response.url().includes("/api/investigations"),
    { timeout: 30000 },
  );
  const firstRecord = page.waitForResponse(isRecordResponse(checkpoints[0]), { timeout: 30000 });
  await page.getByRole("button", { name: "Start the warm-by story" }).click();
  await expect(page.getByRole("heading", { name: "The warm-by story" })).toBeVisible();
  await expect(page.locator(".story-progress")).toContainText(`Step 1 of ${checkpoints.length}`);
  await settleRecord(firstRecord);
  for (let index = 1; index <= 5; index += 1) {
    const pending = page.waitForResponse(isRecordResponse(checkpoints[index]), { timeout: 30000 });
    await stepNext(page, checkpoints, index);
    await settleRecord(pending);
  }
  const at = checkpoints[5];
  await toReasoning(page);
  await expect
    .poll(
      async () => {
        const datetime = await page.locator(".investigation-evaluation-time time").getAttribute("datetime");
        return datetime ? Date.parse(datetime) : NaN;
      },
      { timeout: 30000 },
    )
    .toBe(Date.parse(at));
  const current = `injected interpretation for ${at}`;
  const section = page.locator('section[aria-labelledby="investigation-heading"]');
  await expect(section.locator(".interpretation p")).toContainText(current);
  const earlier = page.getByTestId("earlier-explanations");
  await expect(earlier).toBeAttached();
  const earlierTimes = await earlier.locator("time").evaluateAll((nodes) =>
    nodes.map((node) => node.getAttribute("datetime")),
  );
  expect(earlierTimes.length).toBeGreaterThan(0);
  for (const earlierTime of earlierTimes) {
    expect(earlierTime ? Date.parse(earlierTime) : NaN).toBeLessThan(Date.parse(at));
  }
  for (let index = 0; index <= 4; index += 1) {
    await expect(earlier).toContainText(`injected interpretation for ${checkpoints[index]}`);
  }
  const earlierText = (await earlier.textContent()) ?? "";
  expect(earlierText).not.toContain(current);
});
