# NeoNatal — Session Handoff

> Continuation notes so a fresh session (or you, later) can pick this up with full
> context. Last updated: **2026-07-30**.

---

## TL;DR — where things stand

- **Live on a VPS**: http://187.127.210.133/login (Hostinger, Ubuntu 24.04, KL). Docker Compose stack (Postgres + FastAPI + Next.js), **plain HTTP, bare IP**.
- **Active work**: the **`updates02`** feature — a much fuller baby-registration form + mother's medical record. **Phase 1, 2, 2b done & pushed. Phase 3 (Flutter) is the next task.**
- **Also done & pushed this round**: redesigned **PDF report** (full layout + content incl. maternal + 8-pillar + drawn charts), and a **monitoring navigation fix** (the vital-signs form was unreachable / name-colliding with observation).
- **Local dev** runs via `start.bat` (native: venv + npm + local Postgres). Verified working; DB reseeded.
- **⚠️ The VPS is NOT yet updated** with any of this session's work — needs a `git pull` + rebuild (see below).

---

## What this project is

**Sistem Monitoring Bayi pada Inkubator** — NICU/incubator monitoring. Three clients, one backend:

| Dir | Client | Stack |
|---|---|---|
| `backend/` | API + Postgres | FastAPI, SQLAlchemy 2.0 async, Alembic, JWT |
| `web/` | Oversight dashboard | Next.js 16 (App Router), React 19, Tailwind v4, TanStack Query, Recharts |
| `frontend/` | Bedside data entry | Flutter (Riverpod, Dio, go_router) |

Roles: **admin** (users + audit), **perawat** (all data entry), **dokter** (read-only + PDF).

**Five clinical modules** (naming is confusing — get this right):
- **Monitoring** — vitals (suhu, HR, RR, SpO₂, pain/NIPS, sleep, photo). Route `/baby/[id]/monitoring`, UI label now **"Input Tanda Vital"**.
- **Observation** — 6 pillars / 42 items, each 0–3, max 126. Route `/baby/[id]/observation`, UI label **"Monitoring Bayi (Observasi)"**.
- **Keterlibatan** (parent involvement) — Pillar **6** "Kerjasama dengan Keluarga", 6 items 0–3, max 18.
- **Aksi** — Pillar **8** "Kolaborasi Interprofesional", 6 items 0–3, max 18.
- **Reports** — rollup + PDF (fpdf2).

> ⚠️ **"Monitoring" is two different things.** `/monitoring` = numeric **vital signs**; `/observation` = the 6-pillar **checklist** (was also labeled "Monitoring Bayi" → caused confusion). Fixed 2026-07-30: vitals form relabeled "Input Tanda Vital" and given its own button in the incubator **Menu Aksi** (it had been unreachable). Both are separate APIs/tables by design (different data, cadence, purpose) — kept separate deliberately.

All three scored instruments (observation/involvement/aksi) share a 5-band `category` (Sangat Baik ≥85 … Sangat Kurang <40) and expose a `…/catalog` endpoint (single source of truth in `services/*_catalog.py`). Any observation item scored 0 flips the incubator to `warning`.

> **Two different "8-pillar" frameworks exist** and their numbers collide — don't cross-reference: (a) the IoT clinical framework in `docs/clinical/8 pillar NICU.md` (Pillar 6 = Pain/Stress) used by the **monitoring** field annotations; (b) the nurse-observation instrument (Pillar 6 = Kerjasama, Pillar 8 = Kolaborasi) used by observation/involvement/aksi.

---

## The two git repos (important, easy to trip on)

`backend/` is a **nested git repo of its own** *and* its files are **also tracked by the outer repo**. Same files on disk, two repos:

| | Remote | Default branch |
|---|---|---|
| Outer | `github.com/standungan/NeoNatal` | `main` |
| Nested (`backend/`) | `github.com/standungan/neonatal-backend` | has `main` **and** `backend-version2` |

**Convention used this session:** backend changes go to **both** the outer `main` and the nested **`backend-version2`**; web/frontend changes go to the outer `main` only.

**⚠️ Committing to the nested `backend-version2` — use an isolated git worktree, do NOT switch the shared `backend/` tree's branch.** Switching branches churns `config.py`/`requirements.txt`/`README.md`/`render.yaml` on disk (they differ between `main` and `backend-version2`) and corrupts the outer repo's view. Recipe that worked:

```bash
cd backend
WT=/tmp/nb-v2                      # any path outside the repo
git worktree add "$WT" backend-version2
# copy the changed backend files from backend/ into $WT/, then:
git -C "$WT" add -A && git -C "$WT" commit -m "…"
git -C "$WT" push origin backend-version2
git worktree remove "$WT" --force && git worktree prune
```
The Phase-1/2 backend source dirs (`app/`, `database/`, `alembic/`) are **identical** between `main` and `backend-version2` at base (only `config.py`/deploy files differ), so copying full files gives a clean diff.

Also: **nested `backend` `main` is 5 commits ahead of its origin** (pre-existing deploy commits, unrelated to this work — left unpushed on purpose).

---

## `updates02` feature status (the active work)

Source spec: `docs/specs/updates02/Reguster bayi dan rekam medis ibu.pdf` — turns the simple baby registration into a full NICU intake + structured maternal medical record.

**Design decisions (locked with the user):**
- Mother record → **new `maternal_records` table** (1:1 with baby). `parents` keeps only name/father/phone.
- `usia_masuk_nicu` stored in **jam** (hours).
- No. Registrasi NICU → auto **`NICU-YYYY-XXXX`** (per-year sequence, generated in `baby_service._next_nicu_reg_no`).
- Checklists (indikasi prematur, komplikasi persalinan) → **JSONB arrays** + a "lainnya" free-text.
- DPJP → a user with role `dokter`; Perawat Penerima → the logged-in user (`assigned_by`).
- All new fields **optional** → old registration payloads still work.

| Phase | What | Status |
|---|---|---|
| **1 — DB + backend** | new baby columns, registration cols on assignment, `maternal_records` table, 5 enums, auto reg-number, expanded `BabyCreate`/service, Alembic `b8e4f1c02a37`, `schema.sql` + regenerated seed | ✅ pushed (outer `823bcc4`, version2 `ec278ad`) |
| **2 — web form** | `GET /users/doctors` endpoint (for DPJP dropdown), rebuilt `baby/register` multi-section form, `YesNo`/`CheckboxGroup` controls, `lib/intake.ts` options | ✅ pushed (outer `8be2c89`+`107a437`, version2 `81d6a69`) |
| **2b — report display** | `RegistrationCard`/`BabyIdentityCard`/`MaternalRecordCard` on the report page, `MaternalRecord` TS type | ✅ pushed (outer `22a287d`, web-only) |
| **3 — Flutter** | mobile registration screen still uses the OLD short form | ⬜ **NOT STARTED — next task** |

**Verified working** (local, real browser + DB): full intake registration → `201`, auto `NICU-2026-0001`, DPJP resolved, maternal record with booleans + JSONB checklists persisted; old minimal payload still `201`; report page renders all new cards from seeded data; backward compat intact.

### Post-Phase-2b extras (done & pushed 2026-07-30)
- **PDF report redesign** (`backend/app/services/pdf_service.py`, `report_service.py`, `schemas/report.py`): sectioned layout, 2-col info, warning badges, hand-drawn vital-trend line charts (no new deps), and a dedicated **"Penilaian 8 Pilar"** section = observation (6 pillars) + involvement (Pilar 6) + aksi (Pilar 8) as colored score bars. Now includes registration data, full baby identity, and the maternal record (A–E). `report_service` was extended to include `observation_latest` + `aksi_latest`. Verified by rendering the PDF and viewing the pages (fixed a blank-page break + a chart-label off-by-one-column bug).
- **Monitoring navigation fix** (web): see the ⚠️ note above.
- To render/verify a PDF: hit `GET /api/v1/babies/{id}/report/pdf?token=…`, save the bytes, and open/Read the file. Muhammad Farhan (`cccccccc-0003-0003-0003-000000000003`) is a good rich test case (warning vitals + full maternal record).

### Phase 3 (next task) — Flutter registration
- File: `frontend/lib/features/baby/screens/register_baby_screen.dart` (a stepper).
- Model: `frontend/lib/core/models/baby_model.dart` (+ maybe a new maternal model).
- Needs: extend the payload to match the new `BabyCreate` (baby identity extras, registration fields, `maternal` object), add a DPJP dropdown (call `GET /api/v1/users/doctors`), add the maternal sections. The API contract is done — mirror what `web/app/(app)/baby/register/page.tsx` sends.
- Optional Flutter display: show maternal/registration on the mobile report screen too.

---

## Architecture cheat-sheet

- **Web auth = BFF.** Browser holds an httpOnly cookie `nc_token`; `web/app/api/v1/[...path]/route.ts` proxies every call to FastAPI injecting the Bearer server-side; `web/proxy.ts` gates routes by decoding the JWT. **The browser never sees the backend URL and CORS never applies to the dashboard.** `ALLOWED_ORIGINS` only matters for the Flutter client.
- **Flutter auth** = Bearer header directly to FastAPI; base URL via `--dart-define=API_BASE=…` (default localhost:8000).
- **RBAC deps** (`app/api/deps.py`): `AnyRole`, `PerawatOrAdmin`, `AdminOnly`.
- **Report endpoint** `GET /babies/{id}/report` returns `{baby, monitoring_history, involvement_history, involvement_summary, observation_latest, aksi_latest}`. `baby` includes `maternal` + `current_assignment` (with registration fields). (As of 2026-07-30 `observation_latest`/`aksi_latest` ARE in the payload — added for the PDF's 8-pillar section.)
- **Postman**: `NeoNatal.postman_collection.json` at repo root (37 requests, auto-login token capture; base_url defaults to the VPS).

---

## Landmines (things that already bit us — don't relearn the hard way)

1. **Alembic can't build the DB from scratch.** Initial revision `a7821a4243e6` is `DROP INDEX`-only (autogenerated against an existing DB). Fresh DBs are built from **`backend/database/schema.sql`**, then `alembic stamp head` (NOT `upgrade head`). The Docker stack does this automatically on first boot via `/docker-entrypoint-initdb.d`.
2. **Chrome force-upgrades bare-IP HTTP → HTTPS**, then times out (nothing on :443) → looks like a dead server. Use `http://` explicitly / incognito / disable "Always use secure connections". `COOKIE_SECURE=false` in `.env` is required for the cookie to survive plain HTTP.
3. **`core.autocrlf=true`** on this Windows machine → backend files show as "modified" in git with empty diffs (CRLF vs LF), and container shell files need LF. Root `.gitattributes` pins `*.sh`/Dockerfile/`*.conf`/`*.template` to LF.
4. **`email-validator`** must be in `requirements.txt` (pydantic `EmailStr` imports it lazily) — else clean containers crash-loop at startup. Pinned `2.3.0`.
5. **`package-lock.json`** must be regenerated with **npm 10** (`npx npm@10.9.8 install --package-lock-only`) — the container's node:22-alpine has npm 10 which validates `@emnapi/*` deps that npm 11 skips.
6. **Backgrounded uvicorn via the Bash tool** doesn't pick up `backend/.env` (cwd quirk) — pass env inline for ad-hoc runs. `start.bat` is fine (real cmd, cwd=backend).
7. **`read_page`/screenshots** in the browser tool are flaky for long pages / when the pane is hidden — use `javascript_tool` to inspect the live DOM, and `form.requestSubmit()` (not `button.click()`) to submit React forms reliably.

---

## Running locally (start.bat)

Prereqs (all currently satisfied): PostgreSQL running on :5432, `backend/venv` with deps (incl. `email-validator`), `backend/.env` (points at local `neonatal_db`), `web/node_modules`, `web/.env.local` (`API_BASE_URL=http://localhost:8000`).

```bash
start.bat        # opens 3 windows: backend :8000, web :3000, Flutter :5000
```
Login `admin@neonatal.rs` / `Password123!`. New form: **Daftar Bayi**. Report with new cards: open any baby → **Laporan**.

**Reseed the local DB** (already done; rerun if needed — TRUNCATEs + reinserts, 8 babies + maternal records):
```bash
cd backend
venv/Scripts/python -c "import psycopg2; c=psycopg2.connect(host='localhost',dbname='neonatal_db',user='neonatal_user',password='admin.123'); c.autocommit=True; c.cursor().execute(open('database/seed_data.sql',encoding='utf-8').read())"
```
Local DB is at Alembic head `b8e4f1c02a37`.

---

## Updating the VPS (do this to deploy `updates02`)

```bash
ssh root@187.127.210.133
cd NeoNatal && git pull && docker compose up -d --build
```
- Rebuilds changed images (web + backend this round); **data is safe** (Postgres/uploads in named volumes).
- The backend container runs `alembic upgrade head` on start → the `b8e4f1c02a37` migration applies automatically. Existing data is preserved (migration only adds nullable columns + a new table).
- Verify: log in, open a baby → Laporan → new cards; register a baby → new form.
- Deploy docs: root `DEPLOYMENT.md`. Compose files: `docker-compose.yml` (bare-IP default) + `docker-compose.tls.yml` (HTTPS overlay, for when a domain is added).

---

## Recent commits (this session)

**Outer `standungan/NeoNatal` `main`:** (newest first)
```
db7ee3b fix(web): distinguish vital-signs entry from observation
0f0439a feat(backend): redesign PDF report (layout + full updates02 content)
22a287d feat(web): show maternal record & registration data on the report page
107a437 feat(web): full NICU-intake registration form (Phase 2)
8be2c89 feat(backend): doctors endpoint for DPJP dropdown
823bcc4 feat(backend): expanded NICU intake + maternal record (updates02)
33f2f73 chore: add Postman collection for the API
bbdd463 feat(web): admin-only Add Incubator on the dashboard
447308d docs: rebuild READMEs to match current modules & deployment
```
**Nested `standungan/neonatal-backend` `backend-version2`:**
```
d3e7969 feat(backend): redesign PDF report (layout + full updates02 content)
81d6a69 feat(backend): doctors endpoint for DPJP dropdown
ec278ad feat(backend): expanded NICU intake + maternal record (updates02)
cbf750c docs(readme): rebuild API guide for current modules
47b2e0e fix(deps): pin email-validator
```

---

## Suggested next tasks

1. **Phase 3 — Flutter registration** to match the new form (see above). The main remaining piece of `updates02`.
2. **Redeploy the VPS** with this session's work (steps above) so the live demo reflects it. ← nothing is live yet.
3. **Backend tests** — `backend/tests/` is still empty (pytest is installed). No coverage gates a deploy.
4. Nice-to-have: show maternal/registration on the Flutter report screen; make "Add Incubator" (web) editable; wire the S3 storage stub; add a domain + HTTPS (`docker-compose.tls.yml`).

---

## Key accounts & paths

- Demo logins (all `Password123!`): `admin@neonatal.rs`, `siti.aisyah@neonatal.rs` (perawat), `dr.anisa@neonatal.rs` (dokter).
- API contract: `backend/README.md` (rebuilt this session, current). Design docs: `docs/` (API.md, ERD.md, etc.).
- VPS: `ssh root@187.127.210.133`; IPv4 `187.127.210.133`; host `srv1855835.hstgr.cloud`.
- The old `SECRET_KEY` in `backend/.env` git history is **compromised** (public repo) — production uses a fresh key; never reuse the old one.
