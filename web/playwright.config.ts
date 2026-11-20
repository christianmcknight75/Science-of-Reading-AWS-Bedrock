import { defineConfig, devices } from "@playwright/test";

// Own port so it never clashes with `make dev` (5173). The admin tests mock the API inside the
// tests; the teacher app runs in its built-in mock mode (VITE_API_MODE defaults to mock).
export default defineConfig({
  testDir: "e2e",
  use: { baseURL: "http://localhost:5174" },
  projects: [
    { name: "desktop", use: { viewport: { width: 1280, height: 900 } } },
    {
      // Phone width: teacher screens only. Chromium device emulation (no extra browser needed).
      name: "phone",
      testMatch: /screens\.spec\.ts/,
      use: { ...devices["Pixel 5"], viewport: { width: 375, height: 812 } },
    },
  ],
  webServer: {
    command: "npm run dev -- --port 5174 --strictPort",
    url: "http://localhost:5174",
    reuseExistingServer: !process.env.CI,
  },
});
