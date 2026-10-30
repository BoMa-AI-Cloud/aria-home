import { defineConfig } from "@playwright/test";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const inheritedDbPath = process.env.ARIA_HOME_E2E_DB_PATH;
const dbPath = inheritedDbPath ?? path.join(os.tmpdir(), `aria-home-e2e-${process.pid}.db`);
if (!inheritedDbPath) {
  process.env.ARIA_HOME_E2E_DB_PATH = dbPath;
  for (const suffix of ["", "-wal", "-shm"]) {
    try {
      fs.unlinkSync(`${dbPath}${suffix}`);
    } catch {
    }
  }
}

const frontendPort = process.env.PLAYWRIGHT_FRONTEND_PORT ?? "5173";
const backendPort = process.env.PLAYWRIGHT_BACKEND_PORT ?? "5000";

export default defineConfig({
  testDir: "e2e",
  testIgnore: "public-demo.spec.ts",
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
      command: `python -m flask --app aria_home.app:create_app run --port ${backendPort}`,
      cwd: "../backend",
      url: `http://127.0.0.1:${backendPort}/api/health`,
      reuseExistingServer: false,
      timeout: 60 * 1000,
      env: { ARIA_HOME_MODEL_ENABLED: "0", ARIA_HOME_DB_PATH: dbPath, ARIA_HOME_E2E_HOOKS: "1" },
    },
    {
      command: `npm run dev -- --host 127.0.0.1 --port ${frontendPort} --strictPort`,
      url: `http://127.0.0.1:${frontendPort}`,
      reuseExistingServer: false,
      timeout: 60 * 1000,
    },
  ],
});
