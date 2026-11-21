import { defineConfig } from "@playwright/test";

// Own port so it never clashes with `make dev` (5173). The API is mocked inside the tests.
export default defineConfig({
  testDir: "e2e",
  use: { baseURL: "http://localhost:5174" },
  webServer: {
    command: "npm run dev -- --port 5174 --strictPort",
    url: "http://localhost:5174",
    reuseExistingServer: !process.env.CI,
  },
});
