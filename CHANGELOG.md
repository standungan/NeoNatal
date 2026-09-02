# Changelog

All notable changes to **NeoNatal — Sistem Monitoring Bayi pada Inkubator** (NICU/incubator
monitoring: FastAPI backend · Next.js web dashboard · Flutter bedside client) are documented here.

The format loosely follows [Keep a Changelog](https://keepachangelog.com/). Dates are ISO-8601.
The project is not versioned with SemVer — entries are grouped by milestone date, newest first.

## [Unreleased]

### Pending
- **Push `main`** — 12 commits ahead of `origin/main`, nothing pushed.
- **VPS redeploy** — the live demo is far behind: it has neither the later `updates02` work nor any IoT work.
- **Reconstruct the authenticated firmware** (plan §9) so the unauthenticated `/api/sensors` compatibility route can be retired. The rig currently runs the prototype sketch.
- **Mirror backend changes to the nested `backend-version2` repo** — the IoT work has not been.
- `LatestVitals` and the monitoring/summary endpoints still serialise `Decimal` as JSON strings.

## [2026-09-02] — IoT telemetry, end to end (updates03 P0–P4)

One ESP8266 per incubator streams vitals into the stack: stored, streamed live, charted on
both clients, alarmed against per-incubator thresholds, and aged out. Plan and rationale in
`docs/specs/updates03/IMPLEMENTATION_PLAN.md`.

The rule running through the whole feature: **a null is "no reading", never zero.** The
firmware reports `0` for HR/SpO₂ when nothing is on the probe; that becomes NULL at ingest and
stays NULL through storage, the stream, every chart, the alert engine and the vitals form.

### Added
- **Ingest & devices (P0):** `devices` + `sensor_readings`, `POST /api/v1/telemetry`
  authenticated by `X-Device-Key` (SHA-256 stored, plaintext shown once), admin provisioning
  and revocation, `last_ip` provenance and an optional `allowed_ip` filter. Server assigns the
  timestamp and resolves `baby_id` from the active assignment — neither is the device's to claim.
- **Backfill & chart (P1):** `GET /incubators/{id}/readings`, and small-multiple charts on the
  incubator page with threshold bands from the existing per-incubator settings.
- **Live push (P2):** SSE at `GET /incubators/{id}/stream` with a replayed ring buffer, plus
  the BFF streaming passthrough.
- **Flutter chart (P3):** the same five panels on the incubator screen, polling rather than SSE
  because `dio` streaming does not work on Flutter web.
- **Alerts (P4):** `sensor_alerts` with a 3-reading debounce in both directions, an alert feed
  and acknowledgement (acknowledging is explicitly not resolving).
- **Retention (P4):** 1-minute rollups keeping min/max as well as averages, then pruning raw
  rows past a window; rollup always runs before prune, and prune only touches rows already
  summarised.
- **Vitals autofill (P4):** offered as an action with the reading's age shown, never a silent
  pre-fill.
- **Dashboard (P4):** device badge and per-incubator sparkline, both from one batched query.
- **Five acceptance suites** in `backend/tests/` (129 assertions) and 8 Flutter widget tests.

### Fixed
- **The BFF turned every backend 204 into a 500**, breaking discharge, reset-password and all
  delete routes. It survived because every automated check talked to FastAPI directly, and the
  only sweep through the dashboard's own origin exercised GET routes.
- **`status='warning'` has three independent producers** (alert engine, observation item scored
  0, manual vitals). Both directions are now guarded so neither module silently clears another's
  clinical flag.
- **Perawat could not reach Kolaborasi** in the dashboard although the backend permits it.
- **Flutter showed dokter five write actions** that could only 403.

### Changed
- `incubator_iot/` → `hardware/`; documents grouped under `docs/api|clinical|business|specs`.
- Flutter aksi/involvement catalogs are now fetched rather than duplicated in Dart.

## [2026-07-30] — PDF report redesign & monitoring navigation fix

### Changed
- Redesigned the **PDF report** (`pdf_service.py`, `report_service.py`, `schemas/report.py`): sectioned layout, 2-column info blocks, warning badges, hand-drawn vital-trend line charts (no new deps), and a dedicated **"Penilaian 8 Pilar"** section (observation 6 pillars + involvement Pilar 6 + aksi Pilar 8). Now includes registration data, full baby identity, and the maternal record (A–E). Report payload extended with `observation_latest` + `aksi_latest`.

### Fixed
- Distinguished **vital-signs entry from observation**: the vital-signs form (`/baby/[id]/monitoring`) was unreachable and shared the "Monitoring Bayi" label with the observation checklist. Vitals relabeled **"Input Tanda Vital"** with its own button in the incubator Menu Aksi; observation button → **"Monitoring Bayi (Observasi)"**.

## [2026-07-29] — updates02: expanded NICU intake & maternal record (Phases 1–2b)

Turns the simple baby registration into a full NICU intake + structured maternal medical record.
All new backend fields are optional, so older registration payloads still work.

### Added
- **Phase 1 (DB + backend):** new baby identity/registration columns, `maternal_records` table (1:1 with baby), 5 enums, auto-generated `NICU-YYYY-XXXX` registration number, expanded `BabyCreate` + service, Alembic revision `b8e4f1c02a37`.
- **Phase 2 (web form):** `GET /users/doctors` endpoint for the DPJP dropdown; rebuilt multi-section registration form with `YesNo`/`CheckboxGroup` controls and `lib/intake.ts` options.
- **Phase 2b (report display):** `RegistrationCard` / `BabyIdentityCard` / `MaternalRecordCard` on the report page; `MaternalRecord` TS type.

## [2026-07-27] — Deployment polish & API tooling

### Added
- Admin-only **"Add Incubator"** action on the dashboard.
- **Postman collection** (37 requests, auto-login token capture).

### Changed
- Rebuilt READMEs to match the current modules & deployment.

## [2026-07-26] — Self-hosted VPS deployment (LIVE)

First live deployment — Docker Compose stack on a Hostinger KVM VPS (Ubuntu 24.04),
plain HTTP on a bare IP for demo/testing.

### Added
- **Docker Compose stack** (Postgres + FastAPI + Next.js) for a self-hosted VPS.

### Fixed
- Build the database from `schema.sql` instead of the incomplete Alembic migration chain (the initial revision is `DROP INDEX`-only and can't create tables from scratch).
- Regenerate `package-lock.json` with **npm 10** so `npm ci` passes inside the `node:22-alpine` container.
- Pin `email-validator` (imported lazily by pydantic `EmailStr`) so clean containers no longer crash-loop at startup.

## [2026-07-25] — Deployment prep

### Added
- Initial **Vercel + Render** deployment setup (later superseded by the VPS stack).

## [2026-07-13] — Menu Aksi (Pillar 8 · Kolaborasi Interprofesional)

### Added
- New **Aksi** module across backend + web + Flutter: `aksi_catalog.py` (6 items, 0–3, max 18), `aksi_records` table, catalog/create/list/summary endpoints, Alembic revision `f6d1b3a8e290`, radar + summary UI, and a report card.

### Changed
- Pulled Pillar 8 out of the observation instrument → **"Monitoring Bayi" is now 6 pillars / 42 items / max 126**.
- Updated API docs (`API.md`, `ERD.md`, `api-types.ts`, etc.). Branch merged to `main`.

## [2026-07-10] — Keterlibatan Orang Tua → Pillar 6

### Changed
- Reworked **Parent Involvement** from the FICare 8-domain (0–4) PEI model to **Pillar 6 "Kerjasama dengan Keluarga"** (6 items, 0–3, JSONB `scores`, percentage, 5-band category). Alembic revision `e5c9a2f7d418`. Single source of truth: `involvement_catalog.py`.

### Added
- `GET /involvement/catalog`; catalog-driven entry form + radar/summary; report-page integration.

## [2026-07-08] — Observasi "8 Pilar" observation instrument

### Added
- Premature-baby **observation instrument** ("Monitoring Bayi"): each item scored 0–3, rolls up per-pillar → total % → 5-band category (Sangat Baik ≥85 … Sangat Kurang <40); items ≤1 alarm, any item scored 0 flips the incubator to `warning`. `GET /observation/catalog`, create/list endpoints; catalog-driven entry form + shared radar/summary.

### Changed
- Entry-form radar moved / made collapsible, then kept always visible; Monitoring Bayi card on incubator detail.

### Removed
- Dropped the "Kerjasama dengan Keluarga" pillar from the instrument (covered by the Keterlibatan module). Instrument settled at 6 pillars after the later Aksi split.

## [2026-07-02] — Report data parity

### Fixed
- Surface the `tidak_tersedia` incubator count + full monitoring / FICare data on reports.

## [2026-06-25] — Nurse data entry & incubator humidity

### Added
- Web nurse **data-entry forms**; incubator `kelembapan_inkubator` (humidity) field.

### Changed
- Refreshed dashboard screenshots + API docs.

## [2026-06-24] — Configurable API base & API guide

### Added
- Runtime-configurable API base URL.

### Changed
- Expanded the backend README into a full dashboard API integration guide.

## [2026-06-22] — 8-Pillar NICU framework alignment

### Changed
- Aligned monitoring & parental involvement with the 8-Pillar NICU framework (PR #1).

## [2026-06-17] — Dev tooling

### Changed
- `start.bat` local-dev launcher adjustments.

## [2026-06-13] — Initial release

### Added
- First working build of the Neonatal Care System:
  - **Backend (FastAPI):** JWT auth, RBAC (admin / perawat / dokter), users CRUD (audit-logged), incubators, babies, monitoring + photo upload, involvement, dashboard stats, reports + PDF export, and an audit-logs endpoint.
  - **Flutter web frontend:** all core screens + admin (user management, audit log).
  - **Next.js web dashboard:** login, dashboard, incubator detail, baby report (Recharts + PDF export), admin/users, admin/audit-logs — with httpOnly-cookie BFF auth.
  - Documentation + web dashboard screenshots.
