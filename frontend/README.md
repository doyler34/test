# Dashboard

Next.js (App Router) + TypeScript + Tailwind + shadcn/ui. See the repo root
[`README.md`](../README.md) for the overall architecture.

## Local development (without Docker)

Requires Node 20+ and a running backend (see [`../backend/README.md`](../backend/README.md)).

```bash
cd frontend
npm install
cp .env.example .env.local   # API_INTERNAL_URL defaults to http://localhost:8000
npm run dev
```

Open `http://localhost:3000`. The dev server proxies `/api/*` to
`API_INTERNAL_URL` (see `next.config.mjs`'s `rewrites()`) so the browser only
ever talks to this origin — auth cookies stay same-origin, no CORS setup
needed for local dev.

## Checks

```bash
npm run typecheck
npm run lint
npm run test        # vitest — pure logic (lib/utils, etc.)
npm run build        # production build; also runs Next's own type/lint pass
```

## Layout

```
src/
  app/
    login/                  public login page
    (dashboard)/            authenticated shell (layout.tsx guards auth)
      overview/ downloads/ cache/ users/ system/
  components/
    ui/                     shadcn-style primitives
    dashboard-shell.tsx     responsive nav shell (sidebar / mobile drawer)
  hooks/                    React Query hooks per resource, one per API area;
                            use-sse.ts wraps EventSource for the two live
                            streams (jobs, system metrics) instead of polling
  lib/
    api.ts                  thin fetch wrapper (relative /api/* paths)
    types.ts                TypeScript types mirroring the backend's Pydantic schemas
```
