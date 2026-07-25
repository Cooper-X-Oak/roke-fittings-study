import { defineConfig, devices } from "@playwright/test";

const externalBaseURL = process.env.E2E_BASE_URL;

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: 0,
  workers: 1,
  timeout: 45_000,
  expect: {
    timeout: 10_000,
  },
  reporter: [
    ["list"],
    ["html", { outputFolder: "playwright-report", open: "never" }],
  ],
  use: {
    baseURL: externalBaseURL || "http://127.0.0.1:4173",
    ...devices["Desktop Chrome"],
    viewport: { width: 1440, height: 1000 },
    deviceScaleFactor: 2,
    serviceWorkers: "block",
    reducedMotion: "no-preference",
    trace: "retain-on-failure",
    screenshot: "off",
    video: "retain-on-failure",
    launchOptions: {
      args: [
        "--enable-webgl",
        "--ignore-gpu-blocklist",
        "--use-angle=swiftshader",
      ],
    },
  },
  projects: [
    {
      name: "chromium-3d-gate",
      use: { browserName: "chromium" },
    },
  ],
  webServer: externalBaseURL
    ? undefined
    : {
        command: "node scripts/serve-static.mjs docs 4173",
        url: "http://127.0.0.1:4173/experiment/",
        reuseExistingServer: !process.env.CI,
        timeout: 20_000,
      },
});
