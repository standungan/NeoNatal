# Neonatal Care — Web Dashboard (Next.js)

The desktop oversight client for the Neonatal Care System: live incubator status, baby reports with vital-trend charts and PDF export, plus admin user-management and audit logging.

→ See the [root README](../README.md) for the full-stack overview, and the [backend README](../backend/README.md) for the API.

---

## Tech Stack

| Concern | Choice |
|---|---|
| Framework | Next.js 16 (App Router, Turbopack) |
| UI | React 19, TypeScript |
| Styling | Tailwind CSS v4 (CSS-first `@theme` config) |
| Data | TanStack Query + Axios |
| Charts | Recharts |
| Fonts | Manrope via `next/font` |

---

## Authentication — httpOnly-cookie BFF

The dashboard never holds the JWT in client-readable storage. Instead it uses a **Backend-for-Frontend** pattern:

```
Browser ──▶ Next.js route handlers ──▶ FastAPI
            (httpOnly cookie)          (Bearer header, injected server-side)
```

1. **Login** (`app/api/auth/login/route.ts`) forwards credentials to FastAPI and stores the returned JWT in an **httpOnly cookie** (`nc_token`) — invisible to client JS, mitigating XSS token theft.
2. **All data calls** go to same-origin `/api/v1/*`, handled by the catch-all proxy `app/api/v1/[...path]/route.ts`, which reads the cookie and forwards to FastAPI with the `Authorization: Bearer` header attached. No CORS, no token in the browser.
3. **Route gating** lives in `proxy.ts` (Next 16's renamed `middleware`): it decodes the JWT to redirect unauthenticated users to `/login` and non-admins away from `/admin/*`. Real authorization is still enforced by FastAPI on every request — this is UX gating only.
4. **`/api/auth/me`** lets the client hydrate the current user on load; **`/api/auth/logout`** clears the cookie.

> Because the proxy attaches auth server-side, the PDF report "just works" via a plain `<a href="/api/v1/babies/{id}/report/pdf">` — no token juggling needed.

---

## Project Structure

```
web/
├── app/
│   ├── (app)/                authenticated route group (shared header/shell)
│   │   ├── dashboard/        stats + incubator grid
│   │   ├── incubator/[id]/   incubator + baby detail
│   │   ├── baby/[id]/report/ report: vitals, involvement, history, charts, PDF
│   │   └── admin/            users (CRUD) · audit-logs
│   ├── api/
│   │   ├── auth/             login · logout · me  (cookie handling)
│   │   └── v1/[...path]/     BFF proxy to FastAPI
│   ├── login/                public login page
│   ├── layout.tsx            root layout + Manrope + Providers
│   └── globals.css           Tailwind v4 @theme design tokens
├── components/
│   ├── providers.tsx         QueryClient + Auth context (useAuth)
│   └── ui.tsx                Card, StatCard, StatusBadge, Spinner, …
├── lib/
│   ├── api.ts                axios client (/api/v1) + auth helpers
│   ├── config.ts             API_BASE + cookie name (server-only)
│   ├── types.ts              TS mirrors of FastAPI schemas
│   └── format.ts             dates, status/role labels
└── proxy.ts                  route gating (JWT decode)
```

---

## Getting Started

### Prerequisites
- Node.js 20.9+
- A running [backend](../backend/README.md) on `http://localhost:8000`

### Setup
```bash
npm install
```

Create `web/.env.local`:
```env
# server-side only — never exposed to the browser
API_BASE_URL=http://localhost:8000
```

### Run
```bash
npm run dev      # http://localhost:3000
npm run build    # production build (Turbopack)
npm start        # serve production build
npm run lint     # ESLint (flat config)
```

Log in with a seeded account (e.g. `admin@neonatal.rs` / `Password123!`).

---

## Design System

Tailwind v4 tokens are defined in `app/globals.css` under `@theme`, mirroring the Flutter app's clean-clinical palette so both clients feel identical:

| Token | Value | Use |
|---|---|---|
| `--color-primary` | `#2563eb` | brand / actions |
| `--color-ink` | `#0f172a` | primary text |
| `--color-muted` | `#64748b` | secondary text |
| `--color-ok` / `--color-warn` / `--color-danger` | emerald / amber / red | vital & status semantics |
| `--shadow-card` | soft layered | card depth |

Use the generated utilities directly: `bg-primary`, `text-muted`, `shadow-card`, `rounded-[18px]`, etc.

---

## Next.js 16 Notes

This project targets **Next.js 16** — a few APIs differ from older guides:

- `middleware.ts` is renamed **`proxy.ts`** (exported `proxy` fn, Node.js runtime).
- `cookies()`, `headers()`, and route `params` are **async** — always `await` them.
- Client pages read dynamic segments with `useParams()` to avoid async-params plumbing.
- Turbopack is the default bundler for `dev` and `build`.
