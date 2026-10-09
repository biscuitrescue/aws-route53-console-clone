import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env.E2E_BASE_URL ?? "http://localhost:3000";
const ci = Boolean(process.env.CI);

/**
 * End-to-end tests run against a running stack (frontend + backend). Start both locally,
 * or point E2E_BASE_URL at a deployment, then `npm run test:e2e`.
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  // In CI a stray `test.only` fails the run, a failed test is retried once (and reported
  // as flaky if it then passes), and the HTML report is kept as a workflow artifact.
  forbidOnly: ci,
  retries: ci ? 1 : 0,
  reporter: ci ? [["list"], ["github"], ["html", { open: "never" }]] : [["list"]],
  use: {
    baseURL,
    viewport: { width: 1920, height: 1080 },
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1920, height: 1080 } },
    },
  ],
});
