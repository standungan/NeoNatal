# 🍼 Neonatal Care System

> **Sistem Monitoring Bayi pada Inkubator** — a full-stack system for monitoring newborns in NICU/perinatology incubators, tracking vital signs and parent involvement, with role-based dashboards for nurses, doctors, and administrators.

<p align="center">
  <img alt="FastAPI"  src="https://img.shields.io/badge/FastAPI-Python_3.12-009688?logo=fastapi&logoColor=white">
  <img alt="Flutter"  src="https://img.shields.io/badge/Flutter-3.44-02569B?logo=flutter&logoColor=white">
  <img alt="Next.js"  src="https://img.shields.io/badge/Next.js-16-000000?logo=nextdotjs&logoColor=white">
  <img alt="Postgres" src="https://img.shields.io/badge/PostgreSQL-DB-4169E1?logo=postgresql&logoColor=white">
  <img alt="JWT"      src="https://img.shields.io/badge/Auth-JWT_+_RBAC-EF6C00">
</p>

---

## Overview

Premature and at-risk newborns in incubators need continuous observation — body and incubator temperature, heart rate, SpO₂ — alongside encouragement of **parent involvement** (skin-to-skin time, feeding, interaction), which measurably improves outcomes. This system digitises that workflow:

- **Nurses** record vitals and parent-involvement sessions at the bedside.
- **Doctors** review trends, reports, and exportable PDFs.
- **Admins** manage staff accounts and audit every action.

It ships with **two clients sharing one backend and one design language**:

| Client | Role | Built with |
|--------|------|------------|
| 📱 **Mobile app** | Bedside data entry — register babies, log monitoring & involvement, upload photos | Flutter |
| 🖥️ **Web dashboard** | Oversight — live incubator status, baby reports, vital-trend charts, admin & audit | Next.js |

> **Design narrative:** the mobile app is optimised for *capture* at the cot-side; the web dashboard is optimised for *oversight* on a desktop. Both talk to the same FastAPI service and share an identical clean-clinical visual system.

---

## 📸 Screenshots

### Mobile app (Flutter)

| Login | Dashboard | Incubator Detail |
|---|---|---|
| ![Login](images/login.png) | ![Dashboard](images/dashboard_perawat.png) | ![Incubator detail](images/detail_inkubator.png) |

| Monitoring | Parent Involvement | Report & Trends |
|---|---|---|
| ![Monitoring](images/monitoring%20bayu.png) | ![Parent involvement](images/ParentInvolvement.png) | ![Report](images/report.png) |

### Web dashboard (Next.js)

> _Web dashboard screenshots — drop captures into `images/web/` (login, dashboard, report, admin)._

| Dashboard | Report & Vital Trends | Admin |
|---|---|---|
| ![Dashboard](images/web/dashboard.png) | ![Report](images/web/report.png) | ![Admin](images/web/admin.png) |

---

## ✨ Features

**Monitoring & clinical**
- Baby registration with parent and birth details
- Vital-sign monitoring (suhu bayi/inkubator, heart rate, SpO₂, expression & movement scores)
- Automatic **warning** status when vitals fall outside safe ranges
- Optional photo upload per monitoring session

**Parent involvement**
- Logs feeding/interaction duration and computes an involvement score (0–100)
- Categorised: Rendah / Sedang / Baik / Sangat Baik

**Reporting**
- Per-baby report: current condition, involvement summary, full history
- Interactive **vital-trend charts** with normal-range overlays
- One-click **PDF export**

**Administration**
- User management (create / edit / reset password / activate-deactivate)
- Full **audit log** of every state-changing action

---

## 👥 Roles

| Role | Capabilities |
|------|--------------|
| **Admin** | User management (CRUD + password reset), audit log |
| **Perawat (Nurse)** | Baby registration, monitoring, parent involvement, photo upload, reports |
| **Dokter (Doctor)** | Read-only: dashboard, baby detail, reports/trends, PDF export |

---

## 🏗️ Architecture

```mermaid
flowchart LR
    subgraph Clients
      M["📱 Flutter app<br/>(bedside entry)"]
      W["🖥️ Next.js dashboard<br/>(oversight)"]
    end

    subgraph WebApp["Next.js (BFF)"]
      P["proxy.ts<br/>route gating"]
      R["/api/* route handlers<br/>httpOnly JWT cookie"]
    end

    API["⚙️ FastAPI<br/>JWT · RBAC · services"]
    DB[("🐘 PostgreSQL")]
    S["📁 Photo storage<br/>(local / S3)"]

    M -- "Bearer JWT" --> API
    W --> P --> R -- "injects Bearer<br/>server-side" --> API
    API --> DB
    API --> S
```

- **Mobile** authenticates with FastAPI directly and sends the JWT as a Bearer header.
- **Web** uses a **Backend-for-Frontend (BFF)** pattern: the JWT lives in an **httpOnly cookie** the browser can't read; Next.js route handlers proxy every call to FastAPI with the token injected server-side, and `proxy.ts` gates routes by role. This keeps the token off the client and avoids CORS entirely.

See [`images/04 system arch.png`](images/04%20system%20arch.png) and [`images/05 backend structure diagram.png`](images/05%20backend%20structure%20diagram.png) for the full design.

---

## 🧰 Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | FastAPI, SQLAlchemy 2.0 (async), Alembic, Pydantic v2, python-jose (JWT), Passlib/bcrypt |
| **Database** | PostgreSQL |
| **Mobile** | Flutter, Riverpod, Dio, go_router, fl_chart, google_fonts (Manrope) |
| **Web** | Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS v4, TanStack Query, Recharts |
| **Storage** | Local filesystem (S3-ready) |

---

## 📂 Repository Structure

```
NeoNatal/
├── backend/          FastAPI service
│   ├── app/
│   │   ├── api/v1/    auth, users, incubators, babies, monitoring,
│   │   │              involvement, reports, dashboard, audit
│   │   ├── core/      config, security, database
│   │   ├── models/ · schemas/ · services/ · repositories/
│   │   └── main.py
│   ├── database/     schema.sql, seed_data.sql
│   ├── alembic/      migrations
│   └── requirements.txt
├── frontend/         Flutter mobile app
│   └── lib/
│       ├── core/     theme, router, api client, widgets
│       └── features/ auth, dashboard, baby, monitoring,
│                      involvement, reports, incubator, admin
├── web/              Next.js web dashboard
│   ├── app/          (app)/ pages, api/ route handlers
│   ├── components/ · lib/
│   └── proxy.ts      route gating (Next 16 middleware)
└── images/           diagrams & screenshots
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.12+ · PostgreSQL 14+ · Node.js 20.9+ · Flutter SDK 3.44+

### 1. Database
```bash
createdb neonatal
psql -d neonatal -f backend/database/schema.sql
psql -d neonatal -f backend/database/seed_data.sql
```

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

### Demo accounts
All seeded users share the password **`Password123!`**:

| Role | Email |
|------|-------|
| Admin | `admin@neonatal.rs` |
| Perawat | `siti.aisyah@neonatal.rs` |
| Dokter | `dr.anisa@neonatal.rs` |

---

## 📐 Project Documentation

Design artefacts from the analysis & architecture phases live in [`images/`](images/):

- **Use Case Diagram** — [`01 use case diagram.png`](images/01%20use%20case%20diagram.png)
- **ERD** — [`02 ERD.png`](images/02%20ERD.png)
- **Activity Diagrams** — [`03 activity diagram.png`](images/03%20activity%20diagram.png)
- **System Architecture** — [`04 system arch.png`](images/04%20system%20arch.png)
- **Backend Structure** — [`05 backend structure diagram.png`](images/05%20backend%20structure%20diagram.png)

---

## 🗺️ Status

| Phase | Status |
|-------|--------|
| Analysis · Design · Architecture | ✅ Complete |
| Backend (auth, RBAC, all modules) | ✅ Complete |
| Flutter mobile app | ✅ Complete |
| Next.js web dashboard | ✅ Complete |
| Testing & deployment | ⬜ Planned |

---

<p align="center"><sub>Portfolio project · built with FastAPI, Flutter &amp; Next.js</sub></p>
