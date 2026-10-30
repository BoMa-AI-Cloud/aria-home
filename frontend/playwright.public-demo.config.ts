import { defineConfig } from "@playwright/test";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const runDir = path.join(os.tmpdir(), `aria-home-public-demo-e2e-${process.pid}`);
const sessionsDir = path.join(runDir, "sessions");
const recordedDir = path.join(runDir, "recorded");
fs.mkdirSync(sessionsDir, { recursive: true });
fs.mkdirSync(recordedDir, { recursive: true });

const frontendPort = process.env.PLAYWRIGHT_FRONTEND_PORT ?? "15211";
const backendPort = process.env.PLAYWRIGHT_BACKEND_PORT ?? "15011";

export default defineConfig({
  testDir: "e2e",
  testMatch: "public-demo.spec.ts",
  workers: 1,
  use: { baseURL: `http://127.0.0.1:${frontendPort}` },
  projects: [
    {
      name: "utc",
      use: { channel: "chrome", headless: true, timezoneId: "UTC" },
    },
    {
      name: "los-angeles",
      use: { channel: "chrome", headless: true, timezoneId: "America/Los_Angeles" },
    },
  ],
  webServer: [
    {
      command: `python -m flask --app aria_home.app:create_app run --port ${backendPort} --no-debug`,
      cwd: "../backend",
      url: `http://127.0.0.1:${backendPort}/api/health`,
      reuseExistingServer: false,
      timeout: 60 * 1000,
      env: {
        ARIA_HOME_PUBLIC_DEMO: "1",
        ARIA_HOME_PUBLIC_DEMO_DIR: sessionsDir,
        ARIA_HOME_RECORDED_DIR: recordedDir,
      },
    },
    {
      command: `npm run dev -- --host 127.0.0.1 --port ${frontendPort} --strictPort`,
      url: `http://127.0.0.1:${frontendPort}`,
      reuseExistingServer: false,
      timeout: 60 * 1000,
      env: { PLAYWRIGHT_BACKEND_PORT: backendPort },
    },
  ],
});
