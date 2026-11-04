import { expect, test, type Page, type Response } from "@playwright/test";

const FORBIDDEN_HOSTS = ["graph.facebook.com", "api.meta.ai", "emporia"];
const CLOCK_24 = /\b([01]\d|2[0-3]):([0-5]\d)\b(?!\s*[AP]M)/;

function plainClock(text: string): string {
  return text.replace(new RegExp(CLOCK_24, "g"), (_match, hour: string, minute: string) => {
    const value = Number(hour);
    return `${value % 12 || 12}:${minute} ${value >= 12 ? "PM" : "AM"}`;
  });
}

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
  await expect
    .poll(async () => page.locator(".story-nav").getAttribute("data-story-waiting"), { timeout: 30000 })
    .toBe("false");
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
    "/api/sources?scenario=care_home_v1&at=2026-01-16T23:31:00-05:00",
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
  await expect(story).toContainText("The resident, an older adult, lives alone");
  await stepNext(page, checkpoints, 1);
  await stepNext(page, checkpoints, 2);
  await stepNext(page, checkpoints, 3);
  await stepNext(page, checkpoints, 4);
  await expect(outcome.locator(".outcome-status")).toContainText("Thermostat not reporting");
  for (let index = 5; index < checkpoints.length; index += 1) {
    await stepNext(page, checkpoints, index);
  }
  await expect(page.locator(".story-complete")).toBeVisible();
  await expect(outcome.locator(".outcome-status")).toContainText("Warm-by target met");
  await expect(page.locator(".story-panel")).toContainText("observed");
  await expect(page.locator(".story-panel")).toContainText("first known");
  expect(external).toEqual([]);
});

test("evidence drawer shows computed reasons and no-recording fallback", async ({
  page,
}) => {
  const drawerCheckpoints = await startStory(page);
  await stepNext(page, drawerCheckpoints, 1);
  await stepNext(page, drawerCheckpoints, 2);
  await stepNext(page, drawerCheckpoints, 3);
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
  await stepNext(page, checkpoints, 4);
  await page.getByRole("button", { name: /ARIA.*view/ }).first().click();
  await expect(page.getByRole("heading", { name: "ARIA’s view" })).toBeVisible();
  await expect(page.getByTestId("trace-map")).toBeVisible();
  await expect(page.locator(".trace-steps").locator("li")).not.toHaveCount(0);
  await expect(
    page.locator('[data-testid^="trace-streak-"][data-state="fail"]').first(),
  ).toBeAttached();
  await page
    .locator("section[aria-labelledby='trace-heading']")
    .getByRole("button", { name: "Back to House", exact: true })
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
  await expect(story).toContainText("only then did the simulated HVAC request go out");
  const delivered = page.locator('article[aria-label="HVAC company notification"]', {
    hasText: "Simulated delivery",
  });
  await expect(delivered).toHaveCount(1);
  await delivered.getByText("Show the simulated message").click();
  const fieldsLine = delivered.locator(".fields-sent");
  const fieldKeys = (await fieldsLine.getAttribute("data-fields")) ?? "";
  for (const key of ["property_label", "access_note", "manager_contact_label", "relevant_observations"]) {
    expect(fieldKeys).toContain(key);
  }
  await expect(fieldsLine).toContainText("Contact on file");
  await expect(fieldsLine).not.toContainText("manager_contact_label");
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
  await expect(outcome.locator(".outcome-status")).toContainText("Warm-by target met");
});

test("caregiver notice at 23:31 keeps its 10:46 PM creation facts while House shows the falling room", async ({ page }) => {
  const checkpoints = await startStory(page);
  for (let index = 1; index <= 4; index += 1) {
    await stepNext(page, checkpoints, index);
  }
  const caregiver = page.locator('article[aria-label="Family caregiver notification"]');
  await expect(caregiver).toHaveCount(1);
  await caregiver.getByText("Show the simulated message").click();
  await expect(caregiver).toContainText("Facts when this notice was created (10:46 PM ET)");
  await expect(caregiver).not.toContainText("11:31 PM");
  const permission = page.getByTestId("caregiver-permission");
  await expect(permission).toContainText("62 F");
  await expect(permission).toContainText("10:46 PM");
  await expect(page.locator(".verdict-lead")).toContainText("and falling");
  await expect(page.locator(".verdict-lead")).not.toContainText("62 F");
});

test("completion report arrives after verification and ack changes no outcome", async ({ page }) => {
  const checkpoints = await startStory(page);
  const at0621 = checkpoints.findIndex((checkpoint) => checkpoint.includes("01:41"));
  expect(at0621).toBeGreaterThan(0);
  for (let index = 1; index <= 4; index += 1) {
    await stepNext(page, checkpoints, index);
  }
  const outcome = page.locator("section", {
    has: page.getByRole("heading", { name: "Recovery so far" }),
  });
  await expect
    .poll(async () => outcome.locator(".outcome-time time").getAttribute("datetime"), { timeout: 30000 })
    .toBe(checkpoints[4]);
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
  await page.locator(".story-nav").getByRole("button", { name: "Back to start" }).click();
  await expect(page.locator(".story-progress")).toContainText(`Step 1 of ${checkpoints.length}`);
  const outcome = page.locator("section", {
    has: page.getByRole("heading", { name: "Recovery so far" }),
  });
  const timeline = page.locator("section", {
    has: page.getByRole("heading", { name: "Simulated timeline" }),
  });
  await expect(outcome.locator(".outcome-status")).not.toContainText("Warm-by target met");
  await page.getByRole("navigation", { name: "Pages" }).getByRole("button", { name: "Reasoning" }).click();
  await expect(timeline).not.toContainText("HVAC completion report");
  await expect(page.locator("body")).not.toContainText("Acknowledged, not resolved");
});

test("rapid step changes settle on the last step", async ({ page }) => {
  const checkpoints = await startStory(page);
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await expect(page.locator(".story-progress")).toContainText(
    `Step 5 of ${checkpoints.length}`,
  );
  const outcome = page.locator("section", {
    has: page.getByRole("heading", { name: "Recovery so far" }),
  });
  await expect
    .poll(async () => outcome.locator(".outcome-time time").getAttribute("datetime"), { timeout: 30000 })
    .toBe(checkpoints[4]);
  await expect(outcome.locator(".outcome-status")).toContainText("Thermostat not reporting");
  await expect(outcome.locator(".outcome-status")).not.toContainText("Warm-by target met");
});

test("delayed story create with rapid Next never creates at a later time", async ({ page }) => {
  const checkpoints = await storyCheckpoints(page);
  const createAt = checkpoints[3];
  const later = checkpoints.slice(4);
  const posted: string[] = [];
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/api/investigations*", async (route) => {
    const request = route.request();
    if (request.method() === "POST") {
      const at = new URL(request.url()).searchParams.get("at");
      if (at) posted.push(at);
      if (at === createAt) await gate;
    }
    await route.continue();
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Start the warm-by story" }).click();
  await expect(page.locator(".story-progress")).toContainText(`Step 1 of ${checkpoints.length}`);
  await stepNext(page, checkpoints, 1);
  await stepNext(page, checkpoints, 2);
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await expect(page.locator(".story-progress")).toContainText(`Step 4 of ${checkpoints.length}`);
  await expect
    .poll(async () => page.locator(".story-nav").getAttribute("data-story-waiting"), { timeout: 30000 })
    .toBe("true");
  const next = page.getByRole("button", { name: "Next", exact: true });
  const back = page.getByRole("button", { name: "Back", exact: true });
  await expect(next).toBeDisabled();
  await expect(back).toBeDisabled();
  await expect(page.locator(".story-progress")).toContainText(`Step 4 of ${checkpoints.length}`);
  release();
  await expect
    .poll(async () => page.locator(".story-nav").getAttribute("data-story-waiting"), { timeout: 30000 })
    .toBe("false");
  await expect(page.getByTestId("caregiver-permission").locator(".permission-asked")).toContainText("Asked at", { timeout: 30000 });
  await expect(page.locator(".story-progress")).toContainText(`Step 4 of ${checkpoints.length}`);
  expect(posted.filter((at) => at === createAt)).toHaveLength(1);
  for (const at of later) expect(posted, "no later-time creates").not.toContain(at);
  expect(posted).toContain(createAt);
});

test("story Next stays disabled while a create POST is in flight and 22:46 still creates", async ({ page }) => {
  const checkpoints = await storyCheckpoints(page);
  const holdAt = checkpoints[1];
  const createAt = checkpoints[3];
  const later = checkpoints.slice(4);
  const posted: string[] = [];
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/api/investigations*", async (route) => {
    const request = route.request();
    if (request.method() === "POST") {
      const at = new URL(request.url()).searchParams.get("at");
      if (at) posted.push(at);
      if (at === holdAt) await gate;
    }
    await route.continue();
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Start the warm-by story" }).click();
  await expect(page.locator(".story-progress")).toContainText(`Step 1 of ${checkpoints.length}`);
  await expect
    .poll(async () => page.locator(".story-nav").getAttribute("data-story-waiting"), { timeout: 30000 })
    .toBe("false");
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await expect(page.locator(".story-progress")).toContainText(`Step 2 of ${checkpoints.length}`);
  await expect
    .poll(async () => page.locator(".story-nav").getAttribute("data-story-waiting"), { timeout: 30000 })
    .toBe("true");
  await expect(page.getByRole("button", { name: "Next", exact: true })).toBeDisabled();
  await expect(page.locator(".story-progress")).toContainText(`Step 2 of ${checkpoints.length}`);
  release();
  await expect
    .poll(async () => page.locator(".story-nav").getAttribute("data-story-waiting"), { timeout: 30000 })
    .toBe("false");
  await stepNext(page, checkpoints, 2);
  await stepNext(page, checkpoints, 3);
  await expect(page.getByTestId("caregiver-permission")).toContainText("62 F");
  await expect(page.getByTestId("caregiver-permission")).toContainText("10:46 PM");
  expect(posted.filter((at) => at === holdAt)).toHaveLength(1);
  expect(posted.filter((at) => at === createAt)).toHaveLength(1);
  for (const at of later) expect(posted, "no later-time creates").not.toContain(at);
});

test("story Next stays disabled during the pre-POST GET and the step still settles", async ({ page }) => {
  const checkpoints = await storyCheckpoints(page);
  const holdAt = checkpoints[4];
  const later = checkpoints.slice(5);
  const posted: string[] = [];
  let release!: () => void;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/api/follow-ups/*", async (route) => {
    const at = new URL(route.request().url()).searchParams.get("at");
    if (at === holdAt) await gate;
    await route.continue();
  });
  await page.route("**/api/investigations*", async (route) => {
    if (route.request().method() === "POST") {
      const at = new URL(route.request().url()).searchParams.get("at");
      if (at) posted.push(at);
    }
    await route.continue();
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Start the warm-by story" }).click();
  await expect(page.locator(".story-progress")).toContainText(`Step 1 of ${checkpoints.length}`);
  await stepNext(page, checkpoints, 1);
  await stepNext(page, checkpoints, 2);
  await stepNext(page, checkpoints, 3);
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await expect(page.locator(".story-progress")).toContainText(`Step 5 of ${checkpoints.length}`);
  await expect(page.getByRole("button", { name: "Next", exact: true })).toBeDisabled();
  await expect
    .poll(async () => page.locator(".story-nav").getAttribute("data-story-waiting"), { timeout: 30000 })
    .toBe("true");
  await expect(page.locator(".story-progress")).toContainText(`Step 5 of ${checkpoints.length}`);
  release();
  await expect
    .poll(async () => page.locator(".story-nav").getAttribute("data-story-waiting"), { timeout: 30000 })
    .toBe("false");
  await expect(page.getByTestId("caregiver-permission")).toContainText("62 F", { timeout: 30000 });
  await expect(page.getByTestId("caregiver-permission")).toContainText("10:46 PM");
  expect(posted, "no reuse step creates").not.toContain(holdAt);
  for (const at of later) expect(posted, "no later-time creates").not.toContain(at);
});

test("rapid clicks from start to finish keep the original 62 F request", async ({ page }) => {
  const checkpoints = await startStory(page);
  const permission = page.getByTestId("caregiver-permission");
  for (let index = 1; index < checkpoints.length; index += 1) {
    await page.getByRole("button", { name: "Next", exact: true }).click();
    await expect(page.locator(".story-progress")).toContainText(
      `Step ${index + 1} of ${checkpoints.length}`,
    );
    if (index >= 3) {
      await expect(permission).toContainText("62 F", { timeout: 30000 });
      await expect(permission).toContainText("10:46 PM", { timeout: 30000 });
    }
  }
  await expect(page.locator(".story-complete")).toBeVisible();
  await expect(permission).toContainText("62 F");
  await expect(permission).toContainText("10:46 PM");
});

test("a failed story step load re-enables story navigation", async ({ page }) => {
  const checkpoints = await storyCheckpoints(page);
  const failAt = checkpoints[2];
  await page.route("**/api/follow-ups/*", async (route) => {
    const at = new URL(route.request().url()).searchParams.get("at");
    if (at === failAt) {
      await route.fulfill({ status: 500, body: "boom" });
      return;
    }
    await route.continue();
  });
  await page.route("**/api/investigations*", async (route) => {
    const request = route.request();
    if (request.method() === "POST") {
      const at = new URL(request.url()).searchParams.get("at");
      if (at === failAt) {
        await route.fulfill({ status: 500, body: "boom" });
        return;
      }
    }
    await route.continue();
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Start the warm-by story" }).click();
  await expect(page.locator(".story-progress")).toContainText(`Step 1 of ${checkpoints.length}`);
  await stepNext(page, checkpoints, 1);
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await expect(page.locator(".story-progress")).toContainText(`Step 3 of ${checkpoints.length}`);
  await expect
    .poll(async () => page.locator(".story-nav").getAttribute("data-story-waiting"), { timeout: 30000 })
    .toBe("false");
  await expect(page.getByRole("button", { name: "Next", exact: true })).toBeEnabled();
  await expect(page.getByRole("button", { name: "Back", exact: true })).toBeEnabled();
});

test("starting the story creates its first step at most once", async ({ page }) => {
  const checkpoints = await storyCheckpoints(page);
  const posted: string[] = [];
  await page.route("**/api/investigations*", async (route) => {
    const request = route.request();
    if (request.method() === "POST") {
      const at = new URL(request.url()).searchParams.get("at");
      if (at) posted.push(at);
    }
    await route.continue();
  });
  await page.goto("/");
  await page.waitForLoadState("networkidle");
  await page.getByRole("button", { name: "Start the warm-by story" }).click();
  await expect(page.getByRole("heading", { name: "The warm-by story" })).toBeVisible();
  await expect(page.locator(".story-progress")).toContainText(`Step 1 of ${checkpoints.length}`);
  await expect
    .poll(async () => page.locator(".story-nav").getAttribute("data-story-waiting"), { timeout: 30000 })
    .toBe("false");
  for (let index = 1; index < checkpoints.length; index += 1) {
    await stepNext(page, checkpoints, index);
  }
  await expect(page.locator(".story-complete")).toBeVisible();
  for (const at of checkpoints) {
    expect(posted.filter((entry) => entry === at).length, `creates at ${at}`).toBeLessThanOrEqual(1);
  }
  expect(posted.filter((entry) => entry === checkpoints[0])).toHaveLength(1);
});

test("a hung story step load settles with an error and re-enables navigation", async ({ page }) => {
  const checkpoints = await storyCheckpoints(page);
  const holdAt = checkpoints[4];
  const hangForever = async (route: import("@playwright/test").Route) => {
    await new Promise(() => {});
    await route.continue();
  };
  await page.route("**/api/follow-ups/*", async (route) => {
    const at = new URL(route.request().url()).searchParams.get("at");
    if (at === holdAt) {
      await hangForever(route);
      return;
    }
    await route.continue();
  });
  await page.route("**/api/investigations*", async (route) => {
    const request = route.request();
    if (request.method() === "POST") {
      const at = new URL(request.url()).searchParams.get("at");
      if (at === holdAt) {
        await hangForever(route);
        return;
      }
    }
    await route.continue();
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Start the warm-by story" }).click();
  await expect(page.locator(".story-progress")).toContainText(`Step 1 of ${checkpoints.length}`);
  await stepNext(page, checkpoints, 1);
  await stepNext(page, checkpoints, 2);
  await stepNext(page, checkpoints, 3);
  await page.evaluate(() => {
    (window as unknown as { __ariaStepTimeoutMs?: number }).__ariaStepTimeoutMs = 1500;
  });
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await expect(page.locator(".story-progress")).toContainText(`Step 5 of ${checkpoints.length}`);
  await expect
    .poll(async () => page.locator(".story-nav").getAttribute("data-story-waiting"), { timeout: 30000 })
    .toBe("false");
  await expect(page.getByRole("button", { name: "Next", exact: true })).toBeEnabled();
  await expect(page.getByRole("button", { name: "Back", exact: true })).toBeEnabled();
  const outcome = page.locator("section", {
    has: page.getByRole("heading", { name: "Recovery so far" }),
  });
  await expect(outcome.getByRole("alert")).toContainText("Follow-up not reachable");
});

test("story keeps the original caregiver request while readings update", async ({ page }) => {
  const checkpoints = await startStory(page);
  const permission = page.getByTestId("caregiver-permission");
  const lead = page.locator(".verdict-lead");
  await stepNext(page, checkpoints, 1);
  await stepNext(page, checkpoints, 2);
  await expect(permission).toHaveCount(0);
  await stepNext(page, checkpoints, 3);
  await expect(permission).toBeVisible();
  const requestTexts: string[] = [];
  const askedAt: Array<string | null> = [];
  for (let index = 3; index < checkpoints.length; index += 1) {
    if (index > 3) await stepNext(page, checkpoints, index);
    await expect(permission).toContainText("62 F");
    await expect(permission).toContainText("10:46 PM");
    requestTexts.push(await permission.locator(".permission-text").innerText());
    askedAt.push(await permission.locator(".permission-asked time").getAttribute("datetime"));
  }
  await expect(page.locator(".story-complete")).toBeVisible();
  for (let index = 1; index < requestTexts.length; index += 1) {
    expect(requestTexts[index], "request text frozen").toBe(requestTexts[0]);
    expect(askedAt[index], "request time frozen").toBe(askedAt[0]);
  }
  await expect(lead).toContainText("68");
});

test("visual image is identical at UTC and offset representations", async ({ page }) => {
  const response = await page.request.get("/api/scenarios");
  const body = await response.json();
  const story = body.scenarios.find((item: { id: string }) => item.id === "care_home_v1");
  const at = (story.checkpoints as string[])[4] as string;
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
  ).toContainText("Warm-by target met");
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
  for (let index = 1; index <= 4; index += 1) {
    await stepNext(page, checkpoints, index);
  }
  await expect(page.locator(".verdict-headline")).toContainText("may not be warm by 7:00");
  for (let index = 5; index < checkpoints.length; index += 1) {
    await stepNext(page, checkpoints, index);
  }
  await expect(page.locator(".verdict-headline")).toContainText("The target was met");
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

test("house at 22:46 shows the waiting caregiver request and reasoning stays compact", async ({ page }) => {
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
  await expect(permission).toContainText("62 F");
  await expect(permission).toContainText("10:46 PM");
  await expect(permission).toContainText("No answer yet");
  await expect(page.locator(".verdict-lead")).toContainText("62 F");
  const caregiverNotice = page.locator('article[aria-label="Family caregiver notification"]');
  await caregiverNotice.getByText("Show the simulated message").click();
  await expect(caregiverNotice).toContainText("Facts when this notice was created (10:46 PM ET)");
  await page.getByRole("navigation", { name: "Pages" }).getByRole("button", { name: "Reasoning" }).click();
  await expect(page.getByRole("heading", { name: "ARIA’s view" })).toBeVisible();
  await expect(page.getByTestId("trace-map")).toBeVisible();
  await expect(page.locator(".checks-summary")).toContainText("checks:");
  const height = await page.evaluate(
    () => Math.max(document.body.scrollHeight, document.documentElement.scrollHeight),
  );
  expect(height).toBeLessThan(4500);
});

test("reasoning at 23:31 and 07:01 and laws render with no page errors", async ({ page }) => {
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
    await expect(page.locator("body")).not.toContainText("This section could not be shown");
  };
  const at0231 = checkpoints.findIndex((checkpoint) => checkpoint.includes("23:31"));
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

// Waiting on recordings: the only recorded correction is pinned to the old 23:30 step. Re-enable with its new text once 22:46 is recorded.
test.fixme("watcher corrections ledger lists recorded Original: entries", async ({ page }) => {
  const checkpoints = await startStory(page);
  const at2246 = checkpoints.findIndex((checkpoint) => checkpoint.includes("22:46"));
  expect(at2246).toBeGreaterThan(0);
  for (let index = 1; index <= at2246; index += 1) {
    await stepNext(page, checkpoints, index);
  }
  await page.getByRole("navigation", { name: "Pages" }).getByRole("button", { name: "Reasoning" }).click();
  await expect(page.getByRole("heading", { name: "ARIA’s view" })).toBeVisible();
  await page.locator("summary", { hasText: /ARIA.*Laws/ }).first().click();
  const laws = page.locator("section[aria-labelledby='laws-heading']");
  await laws.locator("summary", { hasText: "Corrections" }).click();
  await expect(laws).toContainText("What the watcher first said:");
  await expect(laws).toContainText("Indoor temp 59.6F, 8.4F below 68F target");
  await expect(laws).toContainText("What it revised to:");
  await expect(laws).toContainText("corrected and verified");
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
  telemetry_missing: "Thermostat not reporting",
  reporting_restored: "Thermostat reporting restored",
  warming_observed: "Warming observed",
  goal_verified: "Target verified",
  goal_not_maintained: "Target no longer held",
  arrival_met: "Warm-by target met",
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
  goal_verified: "Target verified",
  arrival_met: "Warm-by target met",
};

const DECLINED_BANNED = [
  "Technician voice-note report",
  "igniter",
  "Igniter",
  "was replaced",
  "Service visit",
  "HVAC completion report",
  "service_visit",
  "hvac_completion_report",
  "caregiver_hvac_authorized",
  "HVAC may now be contacted",
  "HVAC contacted",
];

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
  let sawRecordedAnswer = false;

  for (let index = 0; index < checkpoints.length; index += 1) {
    if (index > 0) await stepNext(page, checkpoints, index);
    const at = checkpoints[index];
    const userDecided = branch !== "none" && index > 3;
    const scriptedApproved = index >= 4;

    await expect(page.locator(".verdict-headline")).toBeVisible();

    const metrics = await (await page.request.get(`/api/metrics?scenario=care_home_v1&at=${encodeURIComponent(at)}`)).json();
    const apiLastValue = metrics.indoor_trend.last_value as number | null;

    const lead = page.locator(".verdict-lead");
    const insideTile = page.locator(".tiles .tile").nth(0);
    if (apiLastValue !== null) {
      await expect(lead, `lead temperature at ${at}`).toContainText(String(apiLastValue));
      await expect(insideTile.locator(".tile-value"), `inside tile at ${at}`).toContainText(String(apiLastValue));
    }
    await expect(lead, `no per-hour rate at ${at}`).not.toContainText("an hour");

    if (index < 3) {
      await expect(page.locator(".outcome-status strong"), `no follow-up yet at ${at}`).toHaveText(
        "No follow-up scheduled yet",
      );
      await expect(page.getByTestId("caregiver-permission"), `no permission card before the request at ${at}`).toHaveCount(0);
      await expect(page.locator("section[aria-labelledby='who-knows-heading']"), `no notices before the request at ${at}`).toContainText(
        "No notices visible at this step.",
      );
      const activityLine = page.getByTestId("story-activity-line");
      await expect(activityLine, `sourced activity line at ${at}`).toContainText(/computed by code|from a simulated event/);
      await expect(activityLine, `activity keeps ids out of sight at ${at}`).not.toContainText("evt-");
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
    const hvacRow = page.getByTestId("know-row-hvac-company");
    if (permission === null) {
      await expect(card, `no permission card yet at ${at}`).toHaveCount(0);
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
      const wantDecidedAt = userDecided ? checkpoints[3] : scriptedApproved ? "2026-01-16T22:47:00-05:00" : null;
      expect(permission.status, `caregiver status at ${at}`).toBe(wantStatus);
      const wantWords =
        wantStatus === "waiting"
          ? ["No answer yet", "ARIA will not contact HVAC until the caregiver answers"]
          : wantStatus === "approved"
            ? ["Approved by the caregiver at", "HVAC may now be contacted"]
            : ["Declined by the caregiver at", "No HVAC request; verification continues from independent readings."];
      const cardStatus = (await card.locator(".permission-status").textContent()) ?? "";
      const cardText = (await card.locator(".permission-text").textContent()) ?? "";
      const askedAt = await card.locator(".permission-asked time").getAttribute("datetime");
      expect(cardText, `frozen request text at ${at}`).toBe(plainClock(permission.text));
      expect(askedAt, `asked time at ${at}`).toBe(permission.requested_at);
      frozen.push({ text: permission.text, requestedAt: permission.requested_at });
      const decidedCount = await card.locator(".permission-status time").count();
      const decidedAt = decidedCount === 0 ? null : await card.locator(".permission-status time").getAttribute("datetime");
      expect(cardStatus, `caregiver state unmistakable at ${at}`).toContain(wantWords[0]);
      expect(cardStatus, `caregiver effect stated at ${at}`).toContain(wantWords[1]);
      await expect(page.getByTestId("know-row-family-caregiver").locator(".know-row-meta").first(), `caregiver row agrees at ${at}`).toHaveText(
        wantStatus === "waiting" ? "No answer yet" : wantStatus === "approved" ? "Approved" : "Declined",
      );
      const hvacMeta = (await hvacRow.count()) > 0 ? ((await hvacRow.locator(".know-row-meta").textContent()) ?? "") : "";
      expect(hvacMeta, `HVAC row keeps the caregiver sentence to the card at ${at}`).not.toContain(wantWords[0]);
      const visible = (await page.locator("body").innerText()) ?? "";
      expect(visible.split(wantWords[1]).length - 1, `effect said once at ${at}`).toBe(1);
      expect(visible.split(wantWords[0]).length - 1, `state said once at ${at}`).toBe(wantStatus === "waiting" ? 2 : 1);
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

    if (branch === "decline" && index >= 4) {
      const houseText = (await page.locator("body").innerText()) ?? "";
      for (const banned of DECLINED_BANNED) {
        expect(houseText, `no occurrence language on House in the declined path at ${at}`).not.toContain(banned);
      }
      if (index === checkpoints.length - 1) {
        await expect(page.locator(".verdict-headline"), `warm-by missed at ${at}`).toContainText("missed");
      }
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
        plainClock(followups.recorded_investigation.output.interpretation).slice(0, 40),
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
          plainClock(followups.recorded_investigation.output.interpretation).slice(0, 40),
        );
      }
      sawRecordedAnswer = true;
    } else if (!sawRecordedAnswer) {
      await expect(page.getByTestId("earlier-explanations"), `no history without recordings at ${at}`).toHaveCount(0);
    } else {
      // This step has no recording of its own, but earlier steps do: they stay as dated history, never current.
      const earlierTimes = await page.getByTestId("earlier-explanations").locator("time").evaluateAll((nodes) =>
        nodes.map((node) => node.getAttribute("datetime")),
      );
      for (const earlierTime of earlierTimes) {
        expect(earlierTime ? Date.parse(earlierTime) : NaN, `earlier time before ${at}`).toBeLessThan(Date.parse(at));
      }
    }
    const stepsDetails = page.locator(".trace-steps-details");
    if ((await stepsDetails.getAttribute("open")) === null) {
      await stepsDetails.locator("> summary").click();
    }
    const verificationStep = page.locator(".trace-steps li", { hasText: "verification:" });
    await expect(verificationStep, `decision map verification at ${at}`).toContainText(
      plainClock(`— ${(trace.verification.reasons as string[]).join("; ")}`),
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
      ).toContainText(plainClock(permission.text));
    }
    if (branch === "decline" && index >= 4) {
      const reasoningText = (await page.locator("body").innerText()) ?? "";
      for (const banned of DECLINED_BANNED) {
        expect(reasoningText, `no occurrence language on Reasoning in the declined path at ${at}`).not.toContain(banned);
      }
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
  test.setTimeout(120_000);
  await runConsistencyBranch(page, "none");
});

test("guided story never contradicts itself when the caregiver approves at 22:46", async ({ page }) => {
  test.setTimeout(120_000);
  await runConsistencyBranch(page, "approve");
});

test("guided story never contradicts itself when the caregiver declines at 22:46", async ({ page }) => {
  test.setTimeout(120_000);
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
      interpretation: `injected interpretation for ${Date.parse(at)}`,
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
  // Starting the story reuses the page-load create for its first step, so no
  // new record-bearing response follows the click: catch that create instead.
  const firstRecord = page.waitForResponse(isRecordResponse(checkpoints[0]), { timeout: 30000 });
  await page.goto("/");
  await page.waitForResponse(
    (response) => response.request().method() === "POST" && response.url().includes("/api/investigations"),
    { timeout: 30000 },
  );
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
  const current = `injected interpretation for ${Date.parse(at)}`;
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
    await expect(earlier).toContainText(`injected interpretation for ${Date.parse(checkpoints[index])}`);
  }
  const earlierText = (await earlier.textContent()) ?? "";
  expect(earlierText).not.toContain(current);
});

test("explore straight to 01:41 shows verified recovery, 19:20 stays a snapshot", async ({ page }) => {
  const outcome = page.locator("section", {
    has: page.getByRole("heading", { name: "Recovery so far" }),
  });
  await page.goto("/?e2e_at=2026-01-17T01%3A41%3A00-05%3A00");
  await page.getByRole("button", { name: "Explore the app freely" }).click();
  await expect(outcome.locator(".outcome-status")).toContainText("Target verified", { timeout: 30_000 });
  await expect(outcome).not.toContainText("No follow-up scheduled yet");
  await page.goto("/?e2e_at=2026-01-16T19%3A20%3A00-05%3A00");
  await page.getByRole("button", { name: "Explore the app freely" }).click();
  await expect(outcome.locator(".outcome-status strong")).toHaveText("No follow-up scheduled yet", { timeout: 30_000 });
});

test("landing names the hackathon build and Meta models", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("body")).toContainText(
    "Meta's models wrote about 95% of the code and Claude (Anthropic) at least 5%, measured from git history."
  );
  await expect(page.locator("body")).not.toContainText("demo-house");
  await expect(page.locator("body")).toContainText("her daughter is the family caregiver");
  for (const model of [
    "muse-spark-1.3",
    "muse-wonder-1.0",
    "muse-voice-transcribe-1.0",
    "sam-3.1",
    "muse-image-1.0",
  ]) {
    await expect(page.locator("body")).toContainText(model);
  }
  await expect(page.locator("body")).toContainText(
    "replays a synthetic winter night and shows how it gets the right person moving",
  );
});

test("start stays visible at 1280x720 without scrolling", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 720 });
  await page.goto("/");
  const button = page.getByRole("button", { name: "Start the warm-by story" });
  await expect(button).toBeVisible();
  const box = await button.boundingBox();
  expect(box).not.toBeNull();
  expect(box!.y + box!.height).toBeLessThanOrEqual(720);
});

test("the new steps notice at 2 F below and ask at 6 F below", async ({ page }) => {
  const checkpoints = await startStory(page);
  const story = page.locator(".story-panel");
  await stepNext(page, checkpoints, 1);
  await stepNext(page, checkpoints, 2);
  await expect(story.locator("h2")).toHaveText("Noticed: 2 F below target");
  await expect(story).toContainText("No one is asked yet; ARIA asks at 6 F below.");
  await expect(page.getByTestId("caregiver-permission")).toHaveCount(0);
  await expect(page.locator(".story-progress")).toContainText("9:41 PM ET");
  await stepNext(page, checkpoints, 3);
  await expect(story.locator("h2")).toHaveText("6 F below target, so ARIA asks the caregiver");
  await expect(page.getByTestId("caregiver-permission")).toContainText("No answer yet");
  await expect(page.locator(".story-progress")).toContainText("10:46 PM ET");
});

test("the room lead follows the last hour and step 8 reports warming", async ({ page }) => {
  const checkpoints = await startStory(page);
  const lead = page.locator(".verdict-lead");
  const story = page.locator(".story-panel");
  const stepTo = async (time: string) => {
    const target = checkpoints.findIndex((checkpoint) => checkpoint.includes(time));
    for (let index = await currentIndex(); index < target; index += 1) {
      await stepNext(page, checkpoints, index + 1);
    }
  };
  const currentIndex = async () => {
    const text = (await page.locator(".story-progress").innerText()).match(/step (\d+)/i);
    return Number(text?.[1] ?? 1) - 1;
  };
  await stepTo("00:31");
  await expect(lead).toContainText("rising");
  await expect(story.locator("h2")).toHaveText("Warming observed");
  await expect(page.locator(".outcome-status strong")).toHaveText("Warming observed");
  await stepTo("01:41");
  await expect(lead).toContainText("holding at 68");
  await expect(lead).not.toContainText("rising");
  await stepTo("01:51");
  await expect(lead).toContainText("holding at 68");
  await expect(lead).not.toContainText("rising");
});

test("the first alert explains its empty follow-up and the resident row is true", async ({ page }) => {
  const checkpoints = await startStory(page);
  for (let index = 1; index <= 3; index += 1) {
    await stepNext(page, checkpoints, index);
  }
  const outcome = page.locator("section", { has: page.getByRole("heading", { name: "Recovery so far" }) });
  await expect(outcome.locator(".outcome-no-readings")).toContainText("No readings yet since ARIA started this check");
  await expect(outcome).not.toContainText("No replay steps yet");
  await expect(outcome.locator(".outcome-facts")).toHaveCount(0);
  const residentRow = page.getByTestId("know-row-resident");
  await expect(residentRow.locator(".know-row-meta").first()).toHaveText("Told at this step, 10:46 PM ET.");
  await expect(residentRow.locator('article[aria-label="Resident notification"]')).toHaveCount(1);
  await stepNext(page, checkpoints, 4);
  // Approved by now, so the resident has also been told a technician may knock.
  await expect(residentRow.locator(".know-row-meta").first()).toHaveText("Told earlier, at 10:50 PM ET. No new update at this step.");
  await expect(residentRow).toContainText("A technician may knock at your door.");
  await expect(page.locator("body")).not.toContainText("No homeowner update");
});

test("a refused HVAC card shows only that nothing was sent and why", async ({ page }) => {
  const checkpoints = await startStory(page);
  for (let index = 1; index <= 3; index += 1) {
    await stepNext(page, checkpoints, index);
  }
  const refused = page.locator('article[aria-label="HVAC company notification"]');
  await expect(refused).toHaveCount(1);
  await expect(refused).toContainText("Nothing was sent at 10:46 PM ET: the caregiver had not approved HVAC contact.");
  await expect(refused).not.toContainText("Created");
  await expect(refused).not.toContainText("Show the simulated message");
  await expect(refused).not.toContainText("fields sent");
  await expect(page.getByTestId("know-row-hvac-company").locator(".know-row-meta").first()).toHaveText("No request sent.");
  await expect(page.locator(".notices-simulated")).toHaveCount(1);
  expect(((await page.locator("body").innerText()).match(/No message was sent/g) ?? []).length).toBe(1);
});

test("step 5 fits each branch of the caregiver's answer", async ({ page }) => {
  const checkpoints = await startStory(page);
  for (let index = 1; index <= 3; index += 1) {
    await stepNext(page, checkpoints, index);
  }
  await page.getByTestId("caregiver-permission").getByRole("button", { name: "Approve (as the caregiver)" }).click();
  await expect(page.getByTestId("caregiver-permission").locator(".permission-status")).toContainText("Approved by the caregiver");
  await expect(page.locator(".story-panel h2")).toHaveText("Caregiver approves HVAC contact");
  await stepNext(page, checkpoints, 4);
  const story = page.locator(".story-panel");
  await expect(story).toContainText("You approved as the caregiver");
  await expect(story).not.toContainText("In this recorded story");
});

test("step 5 says the recorded answer when the visitor did not answer", async ({ page }) => {
  const checkpoints = await startStory(page);
  for (let index = 1; index <= 4; index += 1) {
    await stepNext(page, checkpoints, index);
  }
  await expect(page.locator(".story-panel")).toContainText("the caregiver approved at 10:47 PM");
  await expect(page.locator(".story-panel")).toContainText("44 minutes after ARIA asked");
});

test("every visible clock is 12-hour and each thing keeps one name", async ({ page }) => {
  test.setTimeout(120_000);
  const checkpoints = await startStory(page);
  const banned = [/\bhomeowner\b/i, /\bgoal\b/i, /warm-by expectation/i, /\bproperty\b/i, /living area/i, /demo-house/, /event:evt-/, /computed:/, /Follow-up rule/, /Revision/, /scoped audiences/, /telemetry/i, /corroboration/i];
  for (let index = 0; index < checkpoints.length; index += 1) {
    if (index > 0) await stepNext(page, checkpoints, index);
    for (const summary of await page.locator(".story-record > summary").all()) await summary.click();
    const house = await page.locator("body").innerText();
    expect(house, `24-hour clock on House at ${checkpoints[index]}`).not.toMatch(CLOCK_24);
    for (const word of banned) expect(house, `${word} on House at ${checkpoints[index]}`).not.toMatch(word);
    await toReasoning(page);
    expect((await page.locator("body").innerText()).split("\n").filter((line) => !line.endsWith("…") && CLOCK_24.test(line)), `24-hour clock on Reasoning at ${checkpoints[index]}`).toEqual([]);
    await pagesNav(page).getByRole("button", { name: "Integrations" }).click();
    const integrations = await page.locator("body").innerText();
    expect(integrations, `24-hour clock on Integrations at ${checkpoints[index]}`).not.toMatch(CLOCK_24);
    for (const word of banned) expect(integrations, `${word} on Integrations at ${checkpoints[index]}`).not.toMatch(word);
    await toHouse(page);
  }
});

// Values below are written from the scenario, not read back from the API.
test("the whole guided story reads correctly from 7:20 PM", async ({ page }) => {
  test.setTimeout(120_000);
  const checkpoints = await startStory(page);
  const onTrack = "The house is on track to be warm by 7:00 AM.";
  const cooling = "The house is cooling. It may not be warm by 7:00 AM.";
  const warming = "The house is warming, but it may not be warm by 7:00 AM.";
  const verified = "The house reached 68 F and held it. The target is verified.";
  const expected: Array<[string, string, string, string, string]> = [
    ["7:20 PM ET", "Plan confirmed, on track", "69 F", "No follow-up scheduled yet", onTrack],
    ["9:00 PM ET", "Evening, still on track", "68.4 F", "No follow-up scheduled yet", onTrack],
    ["9:41 PM ET", "Noticed: 2 F below target", "66 F and falling", "No follow-up scheduled yet", cooling],
    ["10:46 PM ET", "6 F below target, so ARIA asks the caregiver", "62 F and falling", "Unable to verify", cooling],
    ["11:31 PM ET", "Technician on site, room still falling", "59.3 F and falling", "Thermostat not reporting", cooling],
    ["12:21 AM ET", "Thermostat reporting again", "57.6 F and rising", "Thermostat reporting restored", warming],
    ["12:31 AM ET", "Warming observed", "59.7 F and rising", "Warming observed", warming],
    ["1:41 AM ET", "Target verified", "holding at 68 F", "Target verified", verified],
    ["1:51 AM ET", "Technician's report arrives", "holding at 68.4 F", "Target verified", verified],
    ["7:01 AM ET", "Warm-by target met", "holding at 68.2 F", "Warm-by target met", "The house was warm by 7:00 AM. The target was met."],
  ];
  expect(checkpoints).toHaveLength(expected.length);
  for (const [index, [time, title, room, stage, headline]] of expected.entries()) {
    if (index > 0) await stepNext(page, checkpoints, index);
    await expect(page.locator(".story-progress")).toContainText(time);
    await expect(page.locator(".story-panel h2")).toHaveText(title);
    await expect(page.locator(".verdict-lead")).toContainText(room);
    await expect(page.locator(".verdict-headline"), `headline at ${time}`).toHaveText(headline);
    await expect(page.locator(".outcome-status strong")).toHaveText(stage);
    await expect(page.getByTestId("caregiver-permission"), `caregiver request at ${time}`).toHaveCount(index < 3 ? 0 : 1);
  }
});

test("the declined path reads correctly at every step", async ({ page }) => {
  test.setTimeout(120_000);
  const checkpoints = await startStory(page);
  for (let index = 1; index <= 3; index += 1) await stepNext(page, checkpoints, index);
  await page.getByTestId("caregiver-permission").getByRole("button", { name: "Decline (as the caregiver)" }).click();
  await expect(page.getByTestId("caregiver-permission").locator(".permission-status")).toContainText("Declined");
  const cooling = "The house is cooling. It may not be warm by 7:00 AM.";
  await expect(page.locator(".story-panel h2")).toHaveText("Caregiver declines HVAC contact");
  await expect(page.locator(".verdict-headline")).toHaveText(cooling);
  const expected: Array<[string, string, string, string]> = [
    ["11:31 PM ET", "No repair arranged, room still falling", "and falling", cooling],
    ["12:21 AM ET", "Thermostat still silent, house still cold", "56.3 F and falling", cooling],
    ["12:31 AM ET", "No warming observed", "55.7 F and falling", cooling],
    ["1:41 AM ET", "Target not verified", "holding at 52 F", "The house is holding at 52 F. It may not be warm by 7:00 AM."],
    ["1:51 AM ET", "No report: nobody was contacted", "holding at 52 F", "The house is holding at 52 F. It may not be warm by 7:00 AM."],
    ["7:01 AM ET", "Warm-by target missed", "51.4 F", "The house missed the 7:00 AM ET warm-by time: 51.4 F in the living room against the 68 F target."],
  ];
  for (const [offset, [time, title, room, headline]] of expected.entries()) {
    await stepNext(page, checkpoints, offset + 4);
    await expect(page.locator(".story-progress")).toContainText(time);
    await expect(page.locator(".story-panel h2")).toHaveText(title);
    await expect(page.locator(".verdict-lead")).toContainText(room);
    await expect(page.locator(".verdict-headline"), `declined headline at ${time}`).toHaveText(headline);
    await expect(page.locator(".story-panel")).not.toContainText("technician arrived");
  }
});

test("at 12:31 AM story, readings and recovery agree on approval", async ({ page }) => {
  const checkpoints = await startStory(page);
  for (let index = 1; index <= 3; index += 1) await stepNext(page, checkpoints, index);
  await page.getByTestId("caregiver-permission").getByRole("button", { name: "Approve (as the caregiver)" }).click();
  await expect(page.getByTestId("caregiver-permission").locator(".permission-status")).toContainText("Approved");
  for (let index = 4; index <= 6; index += 1) await stepNext(page, checkpoints, index);
  await expect(page.locator(".story-panel h2")).toHaveText("Warming observed");
  await expect(page.locator(".verdict-lead")).toContainText("rising");
  await expect(page.locator(".verification-progression li")).toHaveText([
    "Thermostat reporting restored — Reached",
    "Warming observed — Reached",
    "Target verified — Not reached",
    "Warm-by target met — Not reached",
  ]);
});

test("at 12:31 AM a declined request shows no warming anywhere", async ({ page }) => {
  const checkpoints = await startStory(page);
  for (let index = 1; index <= 3; index += 1) await stepNext(page, checkpoints, index);
  await page.getByTestId("caregiver-permission").getByRole("button", { name: "Decline (as the caregiver)" }).click();
  await expect(page.getByTestId("caregiver-permission").locator(".permission-status")).toContainText("Declined");
  for (let index = 4; index <= 6; index += 1) await stepNext(page, checkpoints, index);
  await expect(page.locator(".story-panel h2")).toHaveText("No warming observed");
  await expect(page.locator(".verdict-lead")).not.toContainText("rising");
  await expect(page.locator(".verification-progression li").nth(1)).toHaveText("Warming observed — Not reached");
});

test("story completion points to the Reasoning proof", async ({ page }) => {
  const checkpoints = await startStory(page);
  for (let index = 1; index < checkpoints.length; index += 1) {
    await stepNext(page, checkpoints, index);
  }
  await expect(page.locator(".story-complete")).toBeVisible();
  await expect(page.locator(".story-proof")).toContainText("See it for yourself:");
  await expect(page.locator(".story-proof")).toContainText(
    "shows the code checks, the recorded model answer and its second review.",
  );
  await page.locator(".story-proof").getByRole("button", { name: "Reasoning" }).click();
  await expect(page.getByRole("heading", { name: "ARIA’s view" })).toBeVisible();
  await expect(page.getByTestId("trace-map")).toBeVisible();
});

test("a step still loading never shows the other branch's outcome", async ({ page }) => {
  const checkpoints = await startStory(page);
  for (let index = 1; index <= 3; index += 1) {
    await stepNext(page, checkpoints, index);
  }
  await page.getByRole("button", { name: /^Decline/ }).click();
  await expect(page.getByRole("button", { name: /^Decline/ })).toHaveCount(0);
  await page.route("**/api/**", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 1200));
    await route.continue();
  });
  await page.getByRole("button", { name: "Next", exact: true }).click();
  const heading = page.locator("#story-heading");
  await expect(heading).toContainText("Loading this step...");
  await expect(heading).not.toContainText(/technician|repair/i);
  await page.unroute("**/api/**");
  await expect(page.locator(".story-nav")).toHaveAttribute("data-story-waiting", "false", { timeout: 30000 });
  await expect(heading).not.toContainText("Loading this step...");
});
