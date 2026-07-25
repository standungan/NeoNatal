# Deployment

This repo holds three deployables. Only the **web dashboard** goes to Vercel.

| Component | Stack | Target | Why |
|---|---|---|---|
| `web/` | Next.js 16 | **Vercel** | App Router + route handlers — native fit |
| `backend/` | FastAPI + Postgres | **Render** (container) | Needs a persistent process, a pooled DB connection, and a writable `uploads/` mount |
| `frontend/` | Flutter | Play Store / APK | Not web-hosted |

```
Browser ──HTTPS──▶ Vercel (Next.js)  ──HTTPS──▶ Render (FastAPI) ──▶ Postgres
                   httpOnly cookie             Bearer token          
                   nc_token                    injected server-side
```

The browser only ever talks to the Vercel origin. `API_BASE_URL` is consumed **server-side only** (`lib/config.ts`), so the backend URL is never shipped to the client and CORS never comes into play for the dashboard.

---

## Order matters: backend first

The Vercel build succeeds without a reachable backend, but every page will 500 at runtime. Deploy `backend/` first and note its public URL.

### 1. Backend → Render

`backend/` is its own git repo (`standungan/neonatal-backend`, default branch `main`) and ships a [Dockerfile](backend/Dockerfile) plus a [render.yaml](backend/render.yaml) blueprint.

**Push first.** Render builds from GitHub, so the deploy-prep commit must be on `origin/main`:

```bash
cd backend
git push origin main
```

**Then deploy the blueprint:** Render → **New → Blueprint** → select the backend repo. `render.yaml` provisions both the Postgres database and the web service, wires `DATABASE_URL` between them, generates a random `SECRET_KEY`, and sets the health check to `/health`.

The one variable it deliberately leaves blank is `ALLOWED_ORIGINS` (marked `sync: false`, so Render prompts you). Set it to your Vercel origin once step 2 is done — or leave it empty for now, since the dashboard reaches the API server-side and never triggers CORS. It only matters for the Flutter client.

**Migrations run themselves.** The container executes `alembic upgrade head` before starting uvicorn, because Render's free plan offers neither a pre-deploy command nor shell access. It's idempotent, so restarts are harmless.

**Verify:** `curl https://<backend>.onrender.com/health` → `{"status":"ok","version":"1.0.0"}`

> **Seeding demo data** needs shell access, which the free plan lacks. Either run `populate_data.py` locally against the Render database using its *External* connection string, or upgrade the instance temporarily.

### 2. Web → Vercel

1. **Import** `standungan/NeoNatal` at [vercel.com/new](https://vercel.com/new).
2. **Set Root Directory to `web`.** This is required — the repo root is not a Node project, so the build fails without it. Framework preset auto-detects as Next.js.
3. **Environment variable** (Production, Preview, Development):

   | Key | Value |
   |---|---|
   | `API_BASE_URL` | `https://<backend>.onrender.com` — **no trailing slash** |

4. **Deploy.** Build settings come from [web/vercel.json](web/vercel.json); no dashboard overrides needed.

Or from the CLI:

```bash
npm i -g vercel
cd web
vercel link
vercel env add API_BASE_URL production
vercel --prod
```

---

## What `web/vercel.json` does

- `regions: ["sin1"]` — pins functions to Singapore. Every dashboard request makes a Vercel→backend hop, so co-locating with an Asia-region backend cuts a round-trip's worth of latency. **Change this if the backend lives elsewhere.**
- `maxDuration: 60` on `app/api/**` — covers PDF report generation and, importantly, Render free-tier cold starts (a spun-down service takes ~50s to wake; the 10s default would time out).
- Security headers plus `no-store` on `/api/*` so authenticated responses are never cached at the edge.

---

## Verifying the deploy

1. `https://<app>.vercel.app/` → redirects to `/login`.
2. Log in. In DevTools → Application → Cookies, `nc_token` must show **HttpOnly ✓ Secure ✓**.
3. Dashboard loads incubator stats — this proves the BFF hop to FastAPI works.
4. Open a baby report → charts render → **Export PDF** downloads a file.
5. Log in as a non-admin and hit `/admin/users` → redirected to `/dashboard` by `proxy.ts`.

If pages render but data is empty, check the Vercel function logs — a bad `API_BASE_URL` shows up as `ECONNREFUSED` or a 404 from the proxy route.

---

## Known limitations

**Photo upload capped at ~4.5 MB.** Vercel Functions reject request bodies above that limit, and monitoring photos pass through the BFF proxy (`app/api/v1/[...path]/route.ts`). Modern phone cameras exceed it. Options: compress client-side before upload, or have the Flutter app POST to the backend directly (it already can — that's what `ALLOWED_ORIGINS` is for).

**Uploaded photos do not survive a backend redeploy.** `storage_service.py` writes to local disk; the S3 branch is a stub (`# S3 path (to be wired when STORAGE_BACKEND=s3)`) even though `boto3` and the `AWS_*` settings are already in place. Render's free tier has an ephemeral filesystem. Either attach a Render persistent disk or finish the S3 backend. Note the web dashboard never *displays* photos, so this only affects the Flutter client.

**Render free tier sleeps after 15 minutes idle.** The first request after that takes ~50s. Fine for a portfolio demo; the 60s function timeout is sized for it. A paid instance or an external pinger removes it.

**JWT expiry is 8 hours, cookie maxAge matches.** No refresh-token flow — users re-login after that.

**Render's free Postgres is deleted after 30 days.** Fine for a demo, but back up anything you care about. Neon or Supabase both offer a free tier without the expiry — swap `DATABASE_URL` and the app is agnostic, since `config.py` normalises whatever scheme the host hands out.

**The old `SECRET_KEY` is public.** `backend/.env` sits in that repo's git history and the repo is public, so the committed key must be treated as compromised. `render.yaml` uses `generateValue: true`, so production gets a fresh random key and never touches the old one. The file is untracked going forward, but purging it from history (git-filter-repo + force-push) is still worth doing if the repo stays public.
