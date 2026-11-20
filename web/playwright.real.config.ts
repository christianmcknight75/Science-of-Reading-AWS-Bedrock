import { defineConfig } from "@playwright/test";

// Real mode: the app talks to a LOCAL API (no mock data). Start the API first, for example:
//   cd api && AUTH_MODE=local QA_ENABLED=true LLM_MODE=fake CORS_ORIGINS=http://localhost:5175 \
//     uv run uvicorn app.main:app --port 8001
// and create an admin with `uv run python -m app.users create-admin ...`, then:
//   REAL_ADMIN_EMAIL=... REAL_ADMIN_PASSWORD=... npm run e2e:real
// The model is a local stand-in (LLM_MODE=fake): Bedrock is blocked (OPEN_QUESTIONS #15).
const API = process.env.REAL_API ?? "http://localhost:8001";
export default defineConfig({
  testDir: "e2e-real",
  workers: 1,
  timeout: 90_000,
  use: { baseURL: "http://localhost:5175", reducedMotion: "reduce" },
  projects: [{ name: "desktop", use: { viewport: { width: 1280, height: 900 } } }],
  webServer: {
    command: "npm run dev -- --port 5175 --strictPort",
    url: "http://localhost:5175",
    env: { VITE_API_MODE: "real", VITE_API_URL: API },
    reuseExistingServer: false,
  },
});
