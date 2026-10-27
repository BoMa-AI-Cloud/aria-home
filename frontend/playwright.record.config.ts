import { defineConfig } from "@playwright/test";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

try {
  const browsers = JSON.parse(
    fs.readFileSync(path.join(process.cwd(), "node_modules/playwright-core/browsers.json"), "utf8"),
  );
  const revision = browsers.browsers.find((b: { name: string }) => b.name === "ffmpeg")?.revision;
  const localAppData = process.env.LOCALAPPDATA;
  if (revision && localAppData) {
    const dest = path.join(localAppData, "ms-playwright", `ffmpeg-${revision}`, "ffmpeg-win64.exe");
    if (!fs.existsSync(dest)) {
      const found = spawnSync("where.exe", ["ffmpeg"], { encoding: "utf8" }).stdout
        .split(/\r?\n/)
        .map((line) => line.trim())
        .find(Boolean);
      if (found) {
        fs.mkdirSync(path.dirname(dest), { recursive: true });
        fs.copyFileSync(found, dest);
      }
    }
  }
} catch {
}

const dbPath = path.join(os.tmpdir(), "aria-home-recording.db");
for (const suffix of ["", "-wal", "-shm"]) {
  try {
    fs.unlinkSync(`${dbPath}${suffix}`);
  } catch {
  }
}

export default defineConfig({
  testDir: "recording",
  testMatch: "**/*.record.ts",
  outputDir: "recordings",
  workers: 1,
  fullyParallel: false,
  retries: 0,
  timeout: 180 * 1000,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:5173",
    viewport: { width: 1280, height: 720 },
    video: { mode: "on", size: { width: 1280, height: 720 } },
    launchOptions: { slowMo: 250 },
  },
  projects: [
    {
      name: "chrome",
      use: { channel: "chrome", headless: true },
    },
  ],
  webServer: [
    {
      command: "python -m flask --app aria_home.app:create_app run --port 5000",
      cwd: "../backend",
      url: "http://127.0.0.1:5000/api/health",
      reuseExistingServer: false,
      timeout: 60 * 1000,
      env: { ARIA_HOME_MODEL_ENABLED: "0", ARIA_HOME_DB_PATH: dbPath },
    },
    {
      command: "npm run dev -- --host 127.0.0.1 --port 5173 --strictPort",
      url: "http://127.0.0.1:5173",
      reuseExistingServer: false,
      timeout: 60 * 1000,
    },
  ],
});
