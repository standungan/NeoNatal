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
│   │   ├── incubator/[id]/   incubator + baby detail (+ Menu Aksi entry points)
│   │   ├── baby/register/    register baby + parent + assign incubator
│   │   ├── baby/[id]/        data-entry forms — monitoring · observation ·
│   │   │                     involvement · aksi — and report (charts + PDF)
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

## Running the Dashboard

The dashboard is a **thin client** — it proxies every request to the FastAPI backend server-side,
so the **backend (and its PostgreSQL database) must be running first**. Start things in this order.

### Prerequisites
- **Node.js 20.9+** (for the dashboard)
- **Python 3.13 and PostgreSQL 14+** (for the backend it talks to)

> Prefer Docker? `docker compose up` from the repo root runs the dashboard, backend and Postgres
> together — see [DEPLOYMENT.md](../DEPLOYMENT.md). The steps below run the dashboard natively.

### 1 — Start the backend + database *(dependency)*
In a **separate terminal**, from the repo root. First run only: create + migrate the database.
```bash
cd backend
python -m venv venv && venv\Scripts\activate      # Windows (source venv/bin/activate on *nix)
pip install -r requirements.txt

# create backend/.env (see backend/README.md), then set up the DB:
createdb neonatal
psql -d neonatal -f database/schema.sql
psql -d neonatal -f database/seed_data.sql
alembic stamp head              # mark the schema current (schema.sql already built all tables)

# run it — keep this terminal open:
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Confirm it's up at **http://localhost:8000/docs**. On later runs you only need the `uvicorn` line
(and `alembic upgrade head` only if a new migration was added after pulling changes).

> Tip: run the backend in its **own** terminal window so it isn't stopped when you restart the dashboard.

### 2 — Configure the dashboard
Create `web/.env.local` (points the server-side proxy at the backend):
```env
# server-side only — never exposed to the browser
API_BASE_URL=http://localhost:8000
```

### 3 — Install & run the dashboard
```bash
cd web
npm install            # first time only
npm run dev            # → http://localhost:3000
```

### 4 — Log in
Open **http://localhost:3000** and sign in with a seeded account, e.g.
`admin@neonatal.rs` / `Password123!` (admin sees everything, incl. user management & audit log).

### Production build
```bash
npm run build          # production build (Turbopack)
npm start              # serve the production build
npm run lint           # ESLint (flat config)
```

### Troubleshooting
- **Login loops / "gagal memuat"** → the backend isn't reachable. Check `http://localhost:8000/docs`
  and that `API_BASE_URL` in `web/.env.local` matches.
- **Port 3000 busy** → stop the other process, or run `npm run dev -- -p 3001`.
- **Blank data after pulling updates** → a new migration may have landed; run `alembic upgrade head`
  in `backend/` (safe once the DB is stamped; see the DB-setup note above).

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
