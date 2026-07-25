# Deployment — VPS

Goal: backend + web dashboard running on your VPS, reachable from home at
`http://<vps-ip>`. Plain HTTP, no domain, no TLS. The Flutter app is not part of
this — it ships as an APK.

```
                          ┌─────────── VPS ───────────┐
Home browser ──:80──▶     │  web (Next.js)            │
                          │    └─▶ backend (FastAPI)  │
Home browser ──:8000──▶   │          └─▶ db (Postgres)│
  (only for /docs)        └───────────────────────────┘
```

Three containers. Postgres is never published — only the other containers can
reach it. The dashboard talks to the backend over the internal compose network,
so `http://backend:8000` never leaves the box and never reaches your browser.

> **This is a testing posture, not a production one.** Over plain HTTP the login
> JWT travels in cleartext. Fine for a portfolio demo you're poking at from home;
> not fine for real patient data. See [Adding HTTPS later](#adding-https-later).

---

## 1. Prepare the VPS

SSH in, then install Docker:

```bash
curl -fsSL https://get.docker.com | sh
```

Open the two ports. **If your VPS is on AWS / Oracle / GCP / Azure, you must
also open them in the cloud console's security group or firewall rules** — the
host firewall alone is not enough, and this is the single most common reason a
deploy looks dead from home:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 8000/tcp
sudo ufw enable
```

**If the VPS has 1 GB RAM or less, add swap before building.** The Next.js build
is the memory-hungry step and gets OOM-killed without it — the symptom is a
build that dies with no useful error:

```bash
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## 2. Clone and configure

```bash
git clone https://github.com/standungan/NeoNatal.git
cd NeoNatal
cp .env.example .env
openssl rand -hex 32          # copy the output
nano .env
```

Three values must change:

| Key | Set it to |
|---|---|
| `VPS_IP` | your server's public IP |
| `POSTGRES_PASSWORD` | anything long — it never leaves the container network |
| `SECRET_KEY` | the `openssl rand -hex 32` output |

Leave `COOKIE_SECURE=false`. Over plain HTTP a `secure` cookie is silently
dropped by the browser, so login would appear to succeed and then bounce you
back to `/login`.

## 3. Build and start

```bash
docker compose up -d --build
```

First run takes a few minutes — it builds two images and pulls Postgres. Then:

```bash
docker compose ps          # all three should be running, db healthy
docker compose logs -f     # Ctrl-C to stop tailing
```

**Migrations need no step of their own.** The backend container runs
`alembic upgrade head` before uvicorn on every start, and it's idempotent.

## 4. Load demo data

The schema exists now, but it's empty — you'd have no account to log in with.

```bash
set -a; . ./.env; set +a
docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  < backend/database/seed_data.sql
```

That loads 8 users, 9 incubators, 8 babies, and about four days of monitoring,
observation, involvement and aksi records. It opens with a `TRUNCATE`, so it's
safe to re-run — and destructive to anything real.

Every seeded account uses the password **`Password123!`**:

| Role | Email |
|---|---|
| Admin | `admin@neonatal.rs` |
| Perawat | `siti.aisyah@neonatal.rs` |
| Dokter | `dr.anisa@neonatal.rs` |

> `backend/populate_data.py` is a local-dev leftover — it hardcodes `localhost`
> and its own credentials, so it won't work against containers. `seed_data.sql`
> replaces it.

## 5. Test from home

1. `http://<vps-ip>:8000/health` → `{"status":"ok","version":"1.0.0"}` — proves the backend is up
2. `http://<vps-ip>/` → redirects to `/login`
3. Log in as `admin@neonatal.rs` / `Password123!`
4. The dashboard shows incubator stats — **this is the real test**, it proves the browser → Next → FastAPI → Postgres chain works end to end
5. Open a baby → **Laporan** → charts render, **Export PDF** downloads
6. Log in as `dr.anisa@neonatal.rs` and try `/admin/users` → bounced to `/dashboard` by `proxy.ts`

---

## Troubleshooting

**Login succeeds then bounces back to `/login`.** `COOKIE_SECURE` is `true` over
HTTP. Set it to `false` in `.env`, then `docker compose up -d web`.

**Nothing loads from home, but `curl localhost` works on the VPS.** Cloud
provider firewall. Check the security group / network rules in the provider
console, not just `ufw status`.

**`port is already allocated` on :80.** Something else is bound — often a
preinstalled Apache or nginx. `sudo ss -tlnp | grep :80`, then
`sudo systemctl disable --now apache2` (or set `WEB_PORT=8080` in `.env`).

**Build dies with no error, or "killed".** Out of memory during `next build`.
Add swap (step 1).

**Dashboard loads but every panel is empty.** The BFF hop is failing:
`docker compose logs backend web`. Usually the backend is unhealthy — check it
reached Postgres.

**`docker compose exec db psql ...` says role does not exist.** The `pgdata`
volume was created with different credentials on an earlier run. Wipe and redo:
`docker compose down -v` (**deletes all data**), then `up -d --build`.

---

## Day-to-day

```bash
docker compose logs -f backend        # tail one service
docker compose restart backend
docker compose down                   # stop (keeps data)
docker compose down -v                # stop AND delete the database

# Deploy an update
git pull && docker compose up -d --build

# Back up the database
set -a; . ./.env; set +a
docker compose exec -T db pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" \
  | gzip > "backup-$(date +%F).sql.gz"

# Back up uploaded photos (they live in a named volume, not the image)
docker run --rm -v neonatal_uploads:/data -v "$PWD:/out" alpine \
  tar czf "/out/uploads-$(date +%F).tar.gz" -C /data .
```

---

## Security

Things that are fine for a home-testing deploy and **not** fine beyond it:

- **Traffic is unencrypted.** The JWT is in cleartext on every request.
- **Port 8000 is open to the internet.** It's there for `/docs` and `/health`
  while you bring the box up. The dashboard does not need it — close it with
  `sudo ufw delete allow 8000/tcp` and drop the `ports:` block from the
  `backend` service once you're done poking around.
- **The old `SECRET_KEY` is burned.** `backend/.env` sits in the public
  `neonatal-backend` repo's git history. Never reuse that key; generate a fresh
  one as in step 2. Purging it from history (`git filter-repo` + force-push) is
  worth doing if that repo stays public.
- **The backend image runs as root**, there's no rate limit on
  `/api/v1/auth/login`, and `backend/tests/` is empty.

---

## Adding HTTPS later

Once you point a domain at the VPS, [docker-compose.tls.yml](docker-compose.tls.yml)
adds nginx + Let's Encrypt on top of the same stack. Its header has the exact
steps; the short version is: two DNS A records (`app.` and `api.`), edit `.env`,
`export COMPOSE_FILE=docker-compose.yml:docker-compose.tls.yml`, then
`./deploy/init-letsencrypt.sh`.

The API gets its **own subdomain** rather than a `/api/` path on the dashboard
host. That isn't stylistic: the dashboard's BFF already owns `/api/*` on its
origin — the Next route handlers there read the httpOnly `nc_token` cookie and
reissue each call to FastAPI with a `Bearer` header. Mounting FastAPI under
`/api/` on the same host would shadow those handlers, the cookie would never be
exchanged, and every dashboard request would 401 in a way that looks like a
backend fault. Full reasoning in
[deploy/nginx/templates/default.conf.template](deploy/nginx/templates/default.conf.template).
