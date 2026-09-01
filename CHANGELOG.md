# Changelog

All notable changes to **NeoNatal — Sistem Monitoring Bayi pada Inkubator** (NICU/incubator
monitoring: FastAPI backend · Next.js web dashboard · Flutter bedside client) are documented here.

The format loosely follows [Keep a Changelog](https://keepachangelog.com/). Dates are ISO-8601.
The project is not versioned with SemVer — entries are grouped by milestone date, newest first.

## [Unreleased]

### Pending
- **Phase 3 — Flutter registration screen** to match the `updates02` NICU-intake + maternal-record form (mirror the payload sent by `web/app/(app)/baby/register/page.tsx`).
- **VPS redeploy** to bring the `updates02` feature + the PDF/navigation work to the live demo (currently the VPS is behind `main`).

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
