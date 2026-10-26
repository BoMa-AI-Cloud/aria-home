import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "e2e",
  use: { baseURL: "http://127.0.0.1:5173" },
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
      env: { ARIA_HOME_MODEL_ENABLED: "0" },
    },
    {
      command: "npm run dev -- --host 127.0.0.1 --port 5173 --strictPort",
      url: "http://127.0.0.1:5173",
      reuseExistingServer: false,
      timeout: 60 * 1000,
    },
  ],
});
