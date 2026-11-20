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

Only `POST /api/ask` exists on the server today. The other calls in `src/api/client.ts` are the proposed
contract; in real mode they show "not ready yet". Admin review page: `#/admin`.
