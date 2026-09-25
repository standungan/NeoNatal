# 🍼 Neonatal Care System

> **Sistem Monitoring Bayi pada Inkubator** — a full-stack, IoT-connected system for NICU/perinatology incubators: sensor units stream each baby's vital signs every three seconds, nurses and doctors record clinical assessments on the 8-pillar NICU framework, and every baby's record rolls up into a report and PDF.

<p align="center">
  <img alt="FastAPI"  src="https://img.shields.io/badge/FastAPI-Python_3.10-009688?logo=fastapi&logoColor=white">
  <img alt="Flutter"  src="https://img.shields.io/badge/Flutter-3.47-02569B?logo=flutter&logoColor=white">
  <img alt="Next.js"  src="https://img.shields.io/badge/Next.js-16-000000?logo=nextdotjs&logoColor=white">
  <img alt="Postgres" src="https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white">
  <img alt="ESP8266"  src="https://img.shields.io/badge/IoT-ESP8266-E7352C?logo=espressif&logoColor=white">
  <img alt="JWT"      src="https://img.shields.io/badge/Auth-JWT_+_RBAC-EF6C00">
</p>

---

## Overview

Premature and at-risk newborns need continuous observation — skin and incubator temperature, humidity, heart rate, SpO₂ — alongside structured care and **parent involvement**, which measurably improves outcomes. A conventional incubator records none of it. This system turns each incubator into a connected bedside:

- **Sensor units** read the baby and the incubator every three seconds and stream to the server — no one has to write the numbers down.
- **Nurses** register babies, chart vitals and assessments, and see live trends and alerts.
- **Doctors** review everything, write clinical notes, and export reports.
- **Admins** manage staff, incubators, sensor devices and thresholds, with every change audited.

Three parts share one backend and one design language:

| Part | Role | Built with |
|------|------|------------|
| 🔌 **Sensor unit** (one per incubator) | Streams skin/air temperature, humidity, heart rate and SpO₂ every 3 s | ESP8266 · MAX30102 · DHT22 · DS18B20 |
| 📱 **Mobile app** | Bedside entry — register babies, chart vitals & assessments, attach photos | Flutter |
| 🖥️ **Web dashboard** | Oversight — ward status, live sensor trends, alerts, reports, administration | Next.js |

> The system monitors and records; it does **not** diagnose, recommend therapy, or control the incubator's heater or humidifier.

---

## 📸 Screenshots

### Mobile app (Flutter)

| Login | Dashboard | Incubator Detail |
|---|---|---|
| ![Login](images/login.png) | ![Dashboard](images/dashboard_perawat.png) | ![Incubator detail](images/detail_inkubator.png) |

| Monitoring | Parent Involvement | Report & Trends |
|---|---|---|
| ![Monitoring](images/monitoring%20bayi.png) | ![Parent involvement](images/ParentInvolvement.png) | ![Report](images/report.png) |

### Web dashboard (Next.js)

| Dashboard | Incubator Detail | Report & Vital Trends |
|---|---|---|
| ![Dashboard](images/web/dashboard.png) | ![Incubator](images/web/incubator.png) | ![Report](images/web/report.png) |

| Monitoring Entry | Parent Involvement Entry | Admin |
|---|---|---|
| ![Monitoring](images/web/monitoring.png) | ![Involvement](images/web/involvement.png) | ![Admin](images/web/admin-users.png) |

Current, annotated screenshots of every screen — including the sensor chart, alerts, baby history and incubator archive — are in the user manual ([`docs/MANUAL.md`](docs/MANUAL.md)).

---

## ✨ Features

**Live IoT monitoring**
- One ESP8266 unit per incubator posts a reading every **3 seconds**, authenticated by a per-device key that is shown **once**, at provisioning, and stored only as a SHA-256.
- The **server** decides which baby a reading belongs to, from the active placement — moving a baby between incubators needs no reflash.
- **Live trend charts** over Server-Sent Events, drawn against each metric's normal band. A probe that is off shows as a **gap, never as zero**, so it cannot be misread as bradycardia.
- **Per-incubator alert thresholds** and a debounced alert engine (3 consecutive breaches to open, 3 in-range readings to resolve); staff acknowledge alerts, but only readings close them.
- Raw readings are kept **7 days**, then rolled up into per-minute avg/min/max that are kept permanently — long histories stay cheap without hiding a short desaturation.

**Clinical records** _(fields aligned with the [8-Pillar NICU framework](docs/clinical/8%20pillar%20NICU.md))_
- Baby registration with birth details, the mother's medical record, and a DPJP (attending doctor)
- Vitals — skin/incubator temperature, humidity, heart rate, respiratory rate, SpO₂ — optionally **pre-filled from the sensor**, always editable before saving
- **Pain/stress score** (NIPS 0–7) and **sleep & comfort** (duration, quality, agitation); automatic **warning** status when values fall outside safe ranges
- A **photo per monitoring record** — thumbnail in the history, full size on click, printed in the PDF
- Three catalog-driven assessment instruments, each item scored **0–4**, rolled up to a percentage and a shared 5-band category (Sangat Baik ≥85 · Baik ≥70 · Cukup ≥55 · Kurang ≥40 · Sangat Kurang <40) and drawn as a radar chart on the dashboard. Forms are built from `…/catalog` endpoints, so every client asks identical questions:
  - **Observation** ("Monitoring Bayi") — **6 pillars / 42 items** (max 168). Any item scored 0 flips the incubator to `warning`.
  - **Keterlibatan Orang Tua** — Pillar 6 "Kerjasama dengan Keluarga": **6 items** (max 24).
  - **Kolaborasi Interprofesional** (Menu Aksi) — Pillar 8: **6 items** (max 24).
- **Doctor's notes**, written only by doctors

**Babies and incubators over time**
- **Riwayat Bayi** — every baby, including those discharged, searchable by name, medical-record or NICU registration number
- Incubators are reused baby after baby: an incubator's charts, alerts and live stream show **only its current occupancy**, and each earlier baby's readings and alerts stay with that baby
- Discharge closes the baby's open alerts, so the empty incubator is immediately ready for the next admission
- **Usage history** per incubator — who was in it, and when

**Reporting**
- Per-baby report: registration, identity and maternal record, monitoring history and vital trends, latest assessments, doctor's note, the baby's **whole-stay sensor history** and alert history
- One-click **PDF export**, including **every monitoring photo** re-encoded small (a report with four photos is ~60 KB)

**Administration**
- Users — create, edit, change role, reset password, deactivate, delete. Deleting an account never removes what it recorded; those records keep naming their author.
- Incubators — auto-numbered; mark unavailable; delete if never used; **archive** if used (off the dashboard, read-only, restorable — its number is never reused)
- IoT devices — provision with a one-time key, optional IP allowlist, revoke
- Full **audit log** of every state-changing action

**Security**
- Role checks on every endpoint, server-side — hidden menus are a convenience, not the control
- Web sessions live in an **httpOnly cookie** behind a Backend-for-Frontend; the browser never holds the JWT
- Patient photos are served only through an authenticated endpoint, never as static files
- Sensor devices can write telemetry and read **nothing**

---

## 👥 Roles

| Role | Capabilities |
|------|--------------|
| **Admin** | Users, incubators (incl. archive), IoT devices, alert thresholds, audit log — plus everything a nurse can do |
| **Perawat (Nurse)** | Register, edit and discharge babies; chart monitoring (with photo), observation, involvement and kolaborasi; acknowledge alerts |
| **Dokter (Doctor)** | Reads all clinical data, reports and PDFs; writes doctor's notes (the only role that can) |
| **Sensor device** | Posts telemetry only — cannot read any patient data |

The backend's guards (`app/api/deps.py`) are the single source of truth; both clients mirror them.

---

## 🏗️ Architecture

```mermaid
flowchart LR
    subgraph Clients
      M["📱 Flutter app<br/>(bedside entry)"]
      B["🖥️ Browser"]
    end
    D["🔌 ESP8266 sensor unit<br/>(one per incubator)"]

    subgraph WebApp["Next.js dashboard (BFF)"]
      P["proxy.ts<br/>route gating"]
      R["/api/* route handlers<br/>httpOnly JWT cookie"]
    end

    API["⚙️ FastAPI<br/>JWT · RBAC · services<br/>SSE stream · alert engine<br/>retention loop"]
    DB[("🐘 PostgreSQL")]
    S["📁 Photo storage<br/>(read through the API)"]

    M -- "Bearer JWT" --> API
    B --> P --> R -- "Bearer injected<br/>server-side" --> API
    D -- "X-Device-Key<br/>every 3 s" --> API
    API --> DB
    API --> S
```

- **Mobile** authenticates with FastAPI directly and sends the JWT as a Bearer header.
- **Web** uses a **Backend-for-Frontend**: the JWT lives in an httpOnly cookie, Next.js route handlers proxy every call with the token injected server-side, and `proxy.ts` gates routes. The token never reaches the client and CORS never applies.
- **Sensor units** authenticate with their device key and never name a patient; the server attributes each reading to the baby currently placed in that incubator.
- Live readings reach the dashboard over **Server-Sent Events** through the same proxy. A retention loop inside the backend rolls raw readings up into per-minute buckets every few hours.

The full design is in the [SRS](docs/deliverables/SRS.md) and the [ERD](docs/deliverables/ERD.md).

---

## 🧰 Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | FastAPI, SQLAlchemy 2.0 (async), Alembic, Pydantic v2, python-jose (JWT), Passlib/bcrypt, fpdf2 + Pillow (PDF) |
| **Database** | PostgreSQL 16 |
| **Mobile** | Flutter, Riverpod, Dio, go_router, fl_chart, google_fonts (Manrope) |
| **Web** | Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS v4, TanStack Query, Recharts |
| **Hardware** | ESP8266 (NodeMCU) · MAX30102 (HR/SpO₂) · DHT22 (air temp/humidity) · DS18B20 (skin probe) · SSD1306 OLED |
| **Deployment** | Docker Compose (Python 3.10, Node 22, Postgres 16); optional nginx + Let's Encrypt overlay |

---

## 📂 Repository Structure

```
NeoNatal/
├── backend/            FastAPI service
│   ├── app/
│   │   ├── api/v1/      auth, users, incubators, babies, monitoring, observation,
│   │   │                involvement, aksi, doctor_notes, reports, dashboard,
│   │   │                telemetry, audit
│   │   ├── core/ · models/ · schemas/ · repositories/ · services/
│   │   ├── jobs/        sensor-data retention loop
│   │   └── main.py
│   ├── alembic/        migrations
│   ├── database/       schema.sql (source of truth), seed_data.sql
│   ├── scripts/        seed_demo_photos.py
│   └── tests/          assert-style check suites
├── frontend/           Flutter mobile app
│   └── lib/
│       ├── core/        theme, router, API client, widgets
│       └── features/    auth, dashboard, incubator, baby, monitoring, observation,
│                        involvement, aksi, doctor_note, reports, admin
├── web/                Next.js dashboard
│   ├── app/             (app)/ pages, api/ BFF route handlers
│   ├── components/ · hooks/ · lib/
│   └── proxy.ts         route gating (Next 16's middleware)
├── hardware/           ESP8266 firmware (allsensors/) and wiring notes
├── docs/               deliverables/, the user manual source, API docs, generators
├── deploy/             nginx + Let's Encrypt for the TLS overlay
├── docker-compose.yml  full stack: Postgres + backend + dashboard
├── DEPLOYMENT.md       server install, updates, backups
├── HANDOFF.md          architecture notes and landmines for the next developer
└── images/             early design diagrams & screenshots
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+ · PostgreSQL 14+ · Node.js 20.9+ · Flutter 3.47 (Dart ≥ 3.3)

> Prefer Docker? The whole stack (Postgres + backend + dashboard) runs with one
> `docker compose up -d --build` — see [DEPLOYMENT.md](DEPLOYMENT.md), which also covers
> updating a running deployment. The steps below are the native path.

### 1. Database
```bash
createdb neonatal
psql -d neonatal -f backend/database/schema.sql
psql -d neonatal -f backend/database/seed_data.sql
```
> The schema is built from `schema.sql`, **not** the Alembic chain (its initial revision can't build
> from empty). Run `alembic stamp head` once after loading `schema.sql`; later migrations then apply
> normally with `alembic upgrade head`.

### 2. Backend (FastAPI)
```bash
cd backend
python -m venv venv && venv\Scripts\activate      # Windows
pip install -r requirements.txt
```
Create `backend/.env`:
```env
SECRET_KEY=change-me-to-a-long-random-string
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/neonatal
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5000
```
Run it:
```bash
uvicorn app.main:app --reload --port 8000
```
API docs at **http://localhost:8000/docs**.

Optional — sample monitoring photos for a demo (illustrated, watermarked *CONTOH*; `--clear` removes them):
```bash
python scripts/seed_demo_photos.py
```

### 3. Web dashboard (Next.js)
```bash
cd web
npm install
# web/.env.local
echo API_BASE_URL=http://localhost:8000 > .env.local
npm run dev        # http://localhost:3000
```

### 4. Mobile app (Flutter)
```bash
cd frontend
flutter pub get
flutter run -d chrome --web-port 5000   # or a device/emulator
```

### 5. Sensor units
Firmware, wiring and per-device configuration are in [`hardware/`](hardware/README.md). Each unit
needs a device key minted from the dashboard (**Detail Inkubator → Pasang Perangkat**).

### Demo accounts
All seeded users share the password **`Password123!`**:

| Role | Email |
|------|-------|
| Admin | `admin@neonatal.rs` |
| Perawat | `siti.aisyah@neonatal.rs` |
| Dokter | `dr.anisa@neonatal.rs` |

---

## ✅ Verifying

There is no pytest suite; verification is a set of assert-style scripts that drive the real API
against the seeded database (backend running on `:8000`):

| Script | Covers | Checks |
|---|---|---|
| `smoke_check.py` | every module answers; RBAC enforced (read-only) | 39 |
| `telemetry_check.py` | the ingest endpoint, NULL-not-zero, audit | 30 |
| `firmware_payload_check.py` | the exact JSON the firmware builds | 5 |
| `stream_check.py` | SSE fan-out and replay | 14 |
| `alert_check.py` | alert debounce and warning ownership | 28 |
| `retention_check.py` | per-minute rollup and safe pruning | 18 |
| `user_delete_check.py` | deleting an account keeps its records | 22 |
| `incubator_history_check.py` | incubator reuse, per-baby history, archive | 78 |
| `photo_check.py` | photo upload/read, thumbnails, PDF, no static path | 24 |

```bash
cd backend
python tests/smoke_check.py        # with the venv active; same for the others
```

Plus `next build` for the dashboard and `flutter analyze` / `flutter test` (8 tests) for the app.
The ones that write data clean up after themselves. Details and gotchas are in [HANDOFF.md](HANDOFF.md).

---

## 📐 Documentation

The contract deliverables are collected in [`docs/deliverables/`](docs/deliverables/), each also as a
printable PDF in [`docs/deliverables/pdf/`](docs/deliverables/pdf/):

| Document | Contents |
|---|---|
| [SRS](docs/deliverables/SRS.md) | Coded functional and non-functional requirements, with traceability to the contract |
| [ERD](docs/deliverables/ERD.md) | All 16 tables, relationships, constraints and retention rules |
| [User manual](docs/MANUAL.md) | Per-role guide for nurses, doctors and admins (HTML build: `docs/deliverables/MANUAL.html`) |
| [API reference](docs/deliverables/api.html) | Every endpoint and the role it requires, generated from the app's OpenAPI schema |
| [UAT report](docs/deliverables/UAT_REPORT.md) | Developer test results, and the acceptance scenarios for the client to run |

Developer-facing: [HANDOFF.md](HANDOFF.md) (architecture, landmines), [DEPLOYMENT.md](DEPLOYMENT.md)
(install, update, backup), [docs/README.md](docs/README.md) (technical docs index). The diagrams in
[`images/`](images/) are the original analysis-phase artefacts; the ERD there predates the IoT tables —
the current one is [`docs/deliverables/ERD.md`](docs/deliverables/ERD.md).

---

## 🗺️ Status

| Area | Status |
|------|--------|
| Backend, web dashboard, mobile app | ✅ Complete |
| IoT telemetry — ingest, live charts, alerts, retention | ✅ Complete |
| Incubator reuse & archive, baby history, monitoring photos in reports | ✅ Complete |
| Containerised deployment (Docker Compose) | ✅ Complete — see [DEPLOYMENT.md](DEPLOYMENT.md) |
| Automated checks | ✅ 9 suites, 258 checks, plus Flutter widget tests |
| Contract documents (SRS, ERD, manual, API reference, UAT report) | ✅ In [`docs/deliverables/`](docs/deliverables/) |
| Firmware end-to-end against a live server | ⏳ Not yet run |
| HTTPS/TLS overlay | ⏳ Prepared, not yet tested |
| Circuit schematic & casing for the sensor unit | ⏳ Wiring notes only |
| Client acceptance testing (UAT Part B) | ⏳ Not yet run |

---

<p align="center"><sub>Built with FastAPI, Flutter, Next.js &amp; ESP8266</sub></p>
