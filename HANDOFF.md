# NeoNatal — Session Handoff

> Continuation notes so a fresh session can pick this up with full context.
> Last updated: **2026-09-02**.

---

## TL;DR — where things stand

- **The IoT telemetry feature (`updates03`) is complete: P0 through P4, all merged to `main`.**
  A physical ESP8266 streams vitals into the stack; they are stored, streamed live,
  charted on both clients, alarmed against per-incubator thresholds, and aged out.
- **129 backend assertions + 8 Flutter widget tests pass.** Five acceptance suites
  in `backend/tests/`, run against a live backend and the seeded DB.
- **Nothing is pushed.** `main` is 12 commits ahead of `origin/main`.
- **⚠️ The VPS is far behind** — it has none of `updates02`'s later work, nor any IoT work.
- **⚠️ The bench ESP8266 is wedged**: it answers ping at `192.168.0.2` but makes no HTTP
  requests after ~2 h of posting into a stopped backend. **Needs a physical power-cycle.**

---

## What this project is

**Sistem Monitoring Bayi pada Inkubator** — NICU/incubator monitoring. Four parts, one backend:

| Dir | Part | Stack |
|---|---|---|
| `backend/` | API + Postgres | FastAPI, SQLAlchemy 2.0 async, Alembic, JWT |
| `web/` | Oversight dashboard | Next.js 16 (App Router), React 19, Tailwind v4, TanStack Query, Recharts |
| `frontend/` | Bedside data entry | Flutter (Riverpod, Dio, go_router, fl_chart) |
| `hardware/` | The rig | ESP8266 sketch + the original Express/React prototype (reference only) |

Roles: **admin** (users, audit, devices, thresholds), **perawat** (all clinical data entry),
**dokter** (read-only + PDF + doctor notes).

**Five clinical modules** (the naming is genuinely confusing — get this right):
- **Monitoring** — vitals (suhu, HR, RR, SpO₂, pain/NIPS, sleep, photo). `/baby/[id]/monitoring`, labelled **"Input Tanda Vital"**.
- **Observation** — 6 pillars / 42 items, each 0–4. `/baby/[id]/observation`, labelled **"Monitoring Bayi (Observasi)"**.
- **Keterlibatan** — Pillar 6 "Kerjasama dengan Keluarga", 6 items 0–4.
- **Aksi** — Pillar 8 "Kolaborasi Interprofesional", 6 items 0–4.
- **Reports** — rollup + PDF (fpdf2).

> ⚠️ **"Monitoring" is two different things.** `/monitoring` = numeric **vital signs**;
> `/observation` = the 6-pillar **checklist**. Separate APIs and tables by design.

> **Two different "8-pillar" frameworks exist** and their numbers collide — don't
> cross-reference: (a) the IoT clinical framework in `docs/clinical/8 pillar NICU.md`
> (Pillar 6 = Pain/Stress); (b) the nurse-observation instrument (Pillar 6 = Kerjasama,
> Pillar 8 = Kolaborasi).

---

## The IoT feature (updates03) — what was built

Plan: `docs/specs/updates03/IMPLEMENTATION_PLAN.md` (it amends `DESIGN.md`; the plan wins).

| Phase | What | Status |
|---|---|---|
| **P0** | `devices` + `sensor_readings`, `POST /api/v1/telemetry` with `X-Device-Key`, admin provisioning | ✅ |
| **P1** | `GET /incubators/{id}/readings`, web chart | ✅ |
| **P2** | SSE stream + ring buffer + BFF passthrough | ✅ |
| **P3** | Flutter chart (polling) | ✅ |
| **P4** | Alert engine, retention, vitals autofill, dashboard sparklines | ✅ |

**Decisions that differ from `DESIGN.md`, and why** — don't "fix" these back:
- **HTTP, not MQTT.** The firmware already does HTTP well; MQTT meant a new container and a new dep.
- **SSE, not WebSocket.** Telemetry is one-way, so it rides the existing cookie→Bearer proxy with no ticket auth.
- **Server-assigned timestamps.** The ESP8266 has no RTC.
- **Identity by device key**, never by a value in the payload.
- **Small multiples, never dual-axis charts.** Two y-scales make the crossing point of two lines meaningless.

**The rule that runs through everything: a null is "no reading", never zero.**
The firmware sends `0` for HR/SpO₂ when nothing is on the probe. That is normalised to
NULL at ingest, stored as NULL, streamed as NULL, breaks the line on every chart (web,
Flutter, sparkline), never opens or resolves an alert, and fills the vitals form as blank.
If you change one of those, change all of them.

---

## Architecture cheat-sheet

- **Web auth = BFF.** Browser holds an httpOnly cookie `nc_token`; `web/app/api/v1/[...path]/route.ts`
  proxies every call to FastAPI injecting the Bearer server-side. **The browser never sees the
  backend URL, and CORS never applies to the dashboard.** `ALLOWED_ORIGINS` matters only for Flutter.
- **Flutter auth** = Bearer straight to FastAPI; base URL via `--dart-define=API_BASE=…`.
- **RBAC deps** (`app/api/deps.py`): `AnyRole`, `PerawatOrAdmin`, `AdminOnly`, `DokterOnly`, `CurrentDevice`.
  **The backend guards decide what the clients show** — check them before gating UI.
- **`incubators.status = 'warning'` has THREE producers**: the alert engine, an observation
  item scored 0, and a manual vitals entry. Never clear it without establishing who set it.
- **Alembic head**: `b5e2a7c9d314` (`incubators.archived_at`, `sensor_alerts.resolved_reason`, per-baby indexes). Before it, `f4b7d2e9a613` (`users.deleted_at` — accounts with records are marked deleted, never removed; see `user_service.delete_user_permanently`).
- **Incubators are reused, and archived rather than deleted.** An incubator that has held a
  baby can't be deleted (its placements are `NO ACTION`, its telemetry `CASCADE`s), so
  `incubator_service.archive_incubator` marks it instead: off the dashboard/admission, read-only,
  device unbound, open alerts closed. Numbering reads archived rows too, so a number is never reused.
- **Incubator-scoped views cover the CURRENT occupancy only** — `/readings`, `/alerts`, the SSE
  replay and dashboard sparklines cut at `AssignmentRepository.occupancy_start` (current
  admission, else last discharge). Earlier data is served per baby: `/babies/{id}/sensor-history`
  (raw ∪ minute rollups) and `/babies/{id}/alerts`. Anything new that reads telemetry by
  incubator must apply the same cut, or the next baby's screen shows the last one's readings.
- **Discharge closes the baby's open sensor alerts** (`resolved_reason='discharged'`). Before, an
  alert left open by a discharged baby flipped the empty incubator back to `warning` on every
  idle reading — and admission requires `kosong`, so the incubator couldn't be reused.

### IoT endpoints

| Method | Path | Auth |
|---|---|---|
| POST | `/api/v1/telemetry` | `X-Device-Key` |
| POST | `/api/sensors` | **none** — legacy, gated by `LEGACY_SENSOR_INGEST` |
| GET | `/api/v1/incubators/{id}/readings` | AnyRole |
| GET | `/api/v1/incubators/{id}/stream` | AnyRole (SSE) |
| GET | `/api/v1/incubators/{id}/alerts` | AnyRole |
| POST | `/api/v1/alerts/{id}/acknowledge` | PerawatOrAdmin |
| GET | `/api/v1/babies/{id}/latest-reading` | AnyRole |
| GET | `/api/v1/babies/{id}/sensor-history` | AnyRole — whole stay, bucketed ≤600 points |
| GET | `/api/v1/babies/{id}/alerts` | AnyRole |
| GET | `/api/v1/incubators/{id}/placements` | AnyRole — usage history |
| POST | `/api/v1/incubators/{id}/archive`, `/restore` | AdminOnly |
| GET/POST/PUT/DELETE | `/api/v1/incubators/{id}/device` | AdminOnly (GET is AnyRole) |

---

## Verifying (do this after any environment change)

There is **no pytest suite**; verification is assert-style scripts plus explicit sweeps.
All need a live backend on `:8000` and the seeded DB.

```bash
cd backend
venv/Scripts/python tests/smoke_check.py       # 39 — every module + RBAC, read-only
venv/Scripts/python tests/telemetry_check.py   # 30 — ingest, 0→NULL, audit
venv/Scripts/python tests/stream_check.py      # 14 — SSE fan-out and replay
venv/Scripts/python tests/alert_check.py       # 28 — debounce, warning ownership
venv/Scripts/python tests/retention_check.py   # 18 — rollup/prune safety
venv/Scripts/python tests/user_delete_check.py # 22 — account deletion keeps its records
venv/Scripts/python tests/incubator_history_check.py  # 78 — reuse, per-baby history, archive
```

Flutter: `flutter analyze` and `flutter test` (8 tests).
Web: `node node_modules/next/dist/bin/next build` — catches type/route errors dev mode hides.

> ⚠️ **Test writes through the BFF (`:3000`), not only the API (`:8000`).** A bug that turned
> every 204 into a 500 — breaking discharge, reset-password and every delete — survived for
> months precisely because every check talked to FastAPI directly.

---

## Landmines (things that already bit us)

1. **Alembic can't build the DB from scratch.** Initial revision `a7821a4243e6` is `DROP INDEX`-only.
   Fresh DBs are built from **`backend/database/schema.sql`**, then `alembic stamp head`
   (NOT `upgrade head`). **Every migration must be mirrored into `schema.sql`** or it does not
   exist on a fresh database.
2. **`sa.Enum` re-creates a Postgres type inside `create_table`** and fails with "already exists".
   Use `postgresql.ENUM(...).create(bind, checkfirst=True)` plus `create_type=False` on the column.
3. **Chrome force-upgrades bare-IP HTTP → HTTPS** and then times out; use `http://` explicitly.
   `COOKIE_SECURE=false` is required for the cookie to survive plain HTTP.
4. **`core.autocrlf=true`** here → `backend/Dockerfile`, `.dockerignore`, `.gitignore`,
   `render.yaml` permanently show as modified with **empty diffs**. Leave them.
5. **`email-validator`** must stay pinned in `requirements.txt` (pydantic imports it lazily).
6. **`package-lock.json`** must be regenerated with **npm 10**.
7. **Backgrounded uvicorn via a tool shell** doesn't pick up `backend/.env`. `start.bat` is fine.
   The preview servers run **without `--reload`** — restart after backend edits.
8. **Screenshots only paint near the top of a long page.** Scroll-then-capture returns blank or
   torn. Hide the cards above the target with `display:none` and capture at scroll 0.
9. **Recharts `ResponsiveContainer` in a CSS grid needs `min-w-0`** on the grid item, or the
   chart never shrinks and the whole page scrolls sideways. The symptom blames the wrong chart.
10. **Pydantic serialises `Decimal` as a JSON string.** `SensorReadingResponse` and
    `SensorAlertResponse` have `field_serializer`s returning floats; **`LatestVitals` and the
    monitoring/summary endpoints still return strings** and would break any arithmetic.

---

## Running locally

```bash
start.bat        # starts Postgres if needed, then backend :8000, web :3000, Flutter :5000
```

Login `admin@neonatal.rs` / `Password123!` (also `siti.aisyah@` perawat, `dr.anisa@` dokter).

This machine has **no system Postgres or Node** — both are portable installs outside the repo:

| Thing | Where | Note |
|---|---|---|
| PostgreSQL 17.2 | `G:\_CODE26\pgsql` | **not a service** — does not survive a reboot |
| Node 22.23.2 | `G:\_CODE26\nodejs` | on the machine PATH |
| Flutter 3.47.2 | `G:\_CODE26\flutter` | on PATH; `flutter config --enable-web` has reset itself once |
| Backend venv | `backend/venv` | **Python 3.10**, not the 3.13 in `.python-version` |

```bash
G:\_CODE26\pgsql\bin\pg_ctl.exe -D G:\_CODE26\pgsql\data -l G:\_CODE26\pgsql\server.log -o "-p 5432" start
G:\_CODE26\pgsql\bin\pg_ctl.exe -D G:\_CODE26\pgsql\data -m fast stop
```

`.claude/launch.json` is intentionally **untracked** — it holds absolute `G:` paths.

---

## The hardware rig

- ESP8266 at `192.168.0.2` on the Advan router (`192.168.0.1`), WiFi SSID `neonatal_incubator`.
  This PC is wired into a **LAN port of the same router** — the router bridges its WiFi and
  LAN ports into one `192.168.0.x/24`, which is why a wireless device and a wired server talk
  directly. (The PC's *WiFi* adapter sits on an unrelated `10.163.1.x` network that cannot
  reach the rig at all — don't bake that address into anything.)
- ⚠️ **The PC's Ethernet address is DHCP and has moved** (`192.168.0.101` → `192.168.0.119`
  during 2026-09-02), while the firmware has `192.168.0.101` compiled in. Until that is pinned,
  a power-cycled rig will post into the void. **Pending: DHCP reservations on the router**
  (`http://192.168.0.1`) — `CC-96-E5-31-EC-2D` → `192.168.0.101` for this PC, and
  `8C-CE-4E-C8-0C-25` → `192.168.0.2` for the ESP, which is also what makes the `allowed_ip`
  filter dependable. Check the PC's current address with `ipconfig` before assuming.
- **The flashed sketch is the PROTOTYPE**: it posts `{incubator_id:"inc1", baby_id:"baby1",
  sensors:{…}}` to `/api/sensors` with no auth. That is why the compatibility route exists,
  enabled by `LEGACY_SENSOR_INGEST=true` in `backend/.env` (**default false**, so a deployment
  gets 404 unless it opts in).
- **The authenticated firmware was lost.** `hardware/` was untracked during the sessions when
  IoT work was excluded from commits, and the sketch was overwritten. Reconstructing it is a
  known follow-up; the contract it must meet is in the plan §9.
- **Coupling is the payload label** (`inc1` → incubator `01`), by explicit choice. IP is
  recorded as provenance and can optionally filter the legacy route, but is never identity —
  DHCP moves it and any LAN host can claim it.

---

## Suggested next tasks

1. **Power-cycle the rig** — it is wedged and no data has arrived since it was left running
   against a stopped backend.
2. **Push `main`** (12 commits) and **redeploy the VPS**, which is far behind. Note
   `LEGACY_SENSOR_INGEST` must stay unset there, which means the rig needs authenticated firmware first.
3. **Reconstruct the authenticated firmware** (plan §9) and retire the legacy route.
4. **Backend changes also belong on the nested `backend-version2` repo** — see below. The IoT
   work has NOT been mirrored there.
5. Fix the remaining `Decimal`-as-string endpoints (landmine 10).
6. Consider surfacing alerts on the dashboard, not only the incubator page.

---

## The two git repos (easy to trip on)

`backend/` is a **nested git repo of its own** *and* its files are **also tracked by the outer repo**.

| | Remote | Branch |
|---|---|---|
| Outer | `github.com/standungan/NeoNatal` | `main` |
| Nested (`backend/`) | `github.com/standungan/neonatal-backend` | `main`, `backend-version2` |

**Committing to the nested `backend-version2` — use an isolated worktree, do NOT switch the
shared `backend/` tree's branch.** Switching churns `config.py`/`requirements.txt`/`README.md`/
`render.yaml` on disk and corrupts the outer repo's view.

```bash
cd backend
WT=/tmp/nb-v2
git worktree add "$WT" backend-version2
# copy changed backend files into $WT, then:
git -C "$WT" add -A && git -C "$WT" commit -m "…"
git -C "$WT" push origin backend-version2
git worktree remove "$WT" --force && git worktree prune
```

Git also reports **dubious ownership** here (the repo moved drives); prefix commands with
`git -c safe.directory="$PWD"` or add it globally.

---

## Key accounts & paths

- Demo logins (all `Password123!`): `admin@neonatal.rs`, `siti.aisyah@neonatal.rs` (perawat),
  `dr.anisa@neonatal.rs` (dokter).
- API contract: `backend/README.md`. Design docs: `docs/api/`, `docs/clinical/`, `docs/specs/`.
- VPS: `ssh root@187.127.210.133`.
- The old `SECRET_KEY` in `backend/.env` git history is **compromised** (public repo) — never reuse it.
- Firmware secrets live in untracked `secrets.h`; the ignore rule is `hardware/**/secrets.h`
  (an archived copy in a subfolder once slipped past a narrower rule).
