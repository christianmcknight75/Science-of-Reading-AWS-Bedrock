# Reading Helper: teacher web app

React + Vite + TypeScript + Tailwind. Teachers only.

```bash
npm ci
npm run dev          # http://localhost:5173 (example mode: no backend needed)
npm run e2e          # Playwright + axe on every screen, desktop and phone width
npm run screenshots  # writes docs-screens/*.png
```

| Env variable                               | Default                 | Meaning                                                                  |
| ------------------------------------------ | ----------------------- | ------------------------------------------------------------------------ |
| `VITE_API_MODE`                            | `mock`                  | `mock` = sample content, clearly marked "Example". `real` = call the API |
| `VITE_API_URL`                             | `http://localhost:8000` | API base URL (real mode)                                                 |
| `VITE_CONTENT_LAST_UPDATED`                | mock date               | ISO date shown in every footer (real mode)                               |
| `VITE_FLAG_BEHAVIOR`, `VITE_FLAG_PROGRESS` | off                     | Parked features; keep off until the sponsor confirms                     |

All endpoints in `src/api/client.ts` are built on the API (`docs/API_CONTRACT.md`), behind its kill switch and a
**fake model** while Bedrock is blocked. Admin review page: `#/admin` (admin accounts only).

## Real mode against the local API

```bash
# 1. Database and migrations (repo root): docker compose up -d db && make migrate
# 2. API with the local stand-in model and the local sign-in issuer (a separate terminal):
cd api && AUTH_MODE=local QA_ENABLED=true LLM_MODE=fake CORS_ORIGINS=http://localhost:5173 \
  uv run uvicorn app.main:app --port 8000
# 3. First admin (password is typed at a prompt):
cd api && uv run python -m app.users create-admin --email you@example.org --name "You" --district "Local"
# 4. The app:
cd web && VITE_API_MODE=real npm run dev
```

`npm run e2e:real` drives the real UI against a running API (see `playwright.real.config.ts`; needs
`REAL_ADMIN_PASSWORD`). Everything the stand-in model writes is labelled "[Fake model]".
