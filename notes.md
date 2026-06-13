# Project Status (Updated)

```text
PHASE 1 — Analysis
────────────────────────
✅ Requirements
✅ Use Case Diagram
✅ ERD
✅ Activity Diagrams

STATUS:
COMPLETED
```

```text
PHASE 2 — Design
────────────────────────
✅ Wireframes
✅ API Specification

STATUS:
COMPLETED
```

```text
PHASE 3 — Architecture
────────────────────────
✅ System Architecture
✅ MVP Backend Structure
✅ MVP Frontend Structure
✅ MVP Deployment Architecture

STATUS:
COMPLETED
```

---

# Current Project Position

```text
Analysis      ██████████ 100%
Design        ██████████ 100%
Architecture  ██████████ 100%

Development   ██████████  83% (Sprint 1–5 complete, Sprint 6 remaining)
Testing       ░░░░░░░░░░   0%
```

---

# PHASE 4 — Development

```text
PHASE 4 — Development
────────────────────────

⬜ Database
⬜ Backend
⬜ Frontend
⬜ Testing
```

---

# Recommended Development Order

## Sprint 1 — Database Foundation

```text
✅ PostgreSQL DDL Final
✅ Alembic Setup
✅ SQLAlchemy Models
⬜ Database Migration (run after DB is provisioned)
✅ Seed Data
```

Deliverable:

```text
backend/
├── database/
│   ├── schema.sql         ✅
│   └── seed_data.sql      ✅
├── alembic/               ✅
│   ├── env.py
│   └── script.py.mako
├── alembic.ini            ✅
├── app/
│   ├── core/
│   │   ├── config.py      ✅
│   │   └── database.py    ✅
│   ├── models/            ✅ (8 models)
│   │   ├── user.py
│   │   ├── incubator.py
│   │   ├── baby.py
│   │   ├── parent.py
│   │   ├── assignment.py
│   │   ├── monitoring.py
│   │   ├── involvement.py
│   │   └── audit.py
│   └── main.py            ✅
├── requirements.txt       ✅
└── .env.example           ✅
```

---

## Sprint 2 — Backend Foundation

```text
✅ FastAPI Project Setup
✅ JWT Authentication
✅ Role-Based Access (AdminOnly / PerawatOrAdmin / AnyRole guards)
✅ User Management API  (CRUD + reset-password + deactivate)
✅ Incubator API        (list / detail / available / create / update)
```

Deliverable:

```text
Endpoints:
  POST   /api/v1/auth/login
  GET    /api/v1/auth/me
  GET    /api/v1/users             [admin]
  POST   /api/v1/users             [admin]
  GET    /api/v1/users/{id}        [admin]
  PUT    /api/v1/users/{id}        [admin]
  POST   /api/v1/users/{id}/reset-password  [admin]
  DELETE /api/v1/users/{id}        [admin]
  GET    /api/v1/incubators        [all roles]
  GET    /api/v1/incubators/available [all roles]
  GET    /api/v1/incubators/{id}   [all roles]
  POST   /api/v1/incubators        [admin]
  PUT    /api/v1/incubators/{id}   [admin]
  GET    /health
```

---

## Sprint 3 — Core Business Features

```text
✅ Baby Registration    (3-step form → single DB transaction)
✅ Parent Information   (created together with baby)
✅ Incubator Assignment (validates status='kosong', updates to 'terisi')
✅ Monitoring Module    (vitals + auto vital-status check)
✅ Photo Upload         (local storage, 5MB limit, JPEG/PNG/WebP)
```

Deliverable:

```text
Endpoints:
  POST   /api/v1/babies                             [perawat/admin]
  GET    /api/v1/babies                             [all roles]
  GET    /api/v1/babies/{id}                        [all roles]
  PUT    /api/v1/babies/{id}                        [perawat/admin]
  POST   /api/v1/babies/{id}/discharge              [perawat/admin]
  POST   /api/v1/babies/{id}/monitoring             [perawat/admin]
  GET    /api/v1/babies/{id}/monitoring             [all roles]
  POST   /api/v1/monitoring/{id}/photo              [perawat/admin]
  GET    /uploads/{baby_id}/{filename}              (static)

Vital alert thresholds:
  HR:        100–160 bpm  → warning if outside
  SpO2:      ≥ 93%        → warning if below
  Suhu Bayi: 36.0–37.5°C  → warning if outside
  (auto-updates incubator status on each monitoring save)
```

---

## Sprint 4 — Reporting Features

```text
✅ Parent Involvement   (scoring formula + CRUD + summary)
✅ Dashboard Statistics (stats + per-incubator live vitals, 2 queries total)
✅ Reports              (full aggregated baby report JSON)
✅ PDF Export           (fpdf2, A4, blue header, tables, 5 sections)
```

Deliverable:

```text
Endpoints:
  GET    /api/v1/dashboard
  POST   /api/v1/babies/{id}/involvement          [perawat/admin]
  GET    /api/v1/babies/{id}/involvement          [all roles]
  GET    /api/v1/babies/{id}/involvement/summary  [all roles]
  GET    /api/v1/babies/{id}/report               [all roles]
  GET    /api/v1/babies/{id}/report/pdf           [all roles]  → download

Involvement scoring formula:
  menyusui_pts  = min(60, durasi_menyusui * 2)       (30 min = max)
  interaksi_pts = min(40, durasi_interaksi * 40/60)  (60 min = max)
  skor = menyusui_pts + interaksi_pts   (0-100)
  0-25 Rendah | 26-50 Sedang | 51-75 Baik | 76-100 Sangat Baik
```

---

## Sprint 5 — Frontend Integration

```text
✅ Login Screen         (JWT auth, error handling, secure storage)
✅ Dashboard            (stats cards, incubator list, live vitals, pull-to-refresh)
✅ Incubator Detail     (baby info, action menu)
✅ Registration         (3-step PageView form → single API call)
✅ Monitoring           (vitals input, 1–5 score chips, photo picker, warning snackbar)
✅ Keterlibatan OT      (live score preview mirrors backend formula)
✅ Reports              (vitals summary, involvement summary, monitoring history, PDF export)
✅ API Integration      (Dio + JWT interceptor, go_router auth guard, Riverpod state)
```

Deliverable:

```text
frontend/
├── pubspec.yaml              (Riverpod, Dio, go_router, fl_chart, image_picker...)
├── lib/
│   ├── main.dart / app.dart
│   ├── core/
│   │   ├── api/              (client + endpoints)
│   │   ├── models/           (auth, baby, monitoring, involvement, dashboard)
│   │   ├── providers/        (auth_provider with secure storage restore)
│   │   ├── router/           (go_router with auth redirect guard)
│   │   ├── theme/            (AppTheme + AppColors)
│   │   └── widgets/          (StatCard, StatusBadge, ScoreChips)
│   └── features/             (7 feature folders, each with screen + optional provider)
```

---

## Sprint 6 — Testing & Deployment

```text
⬜ UAT
⬜ Bug Fixing
⬜ VPS Setup
⬜ PostgreSQL Production DB
⬜ Deployment
```

Deliverable:

```text
MVP ready for demonstration
```

---

# Updated Master Status

```text
PHASE 1 — Analysis
✅ COMPLETED

PHASE 2 — Design
✅ COMPLETED

PHASE 3 — Architecture
✅ COMPLETED

PHASE 4 — Development
⬜ Database
⬜ Backend
⬜ Frontend
⬜ Testing
```

The next task is clear:

> **PHASE 4 → Database → Final PostgreSQL DDL Package (schema.sql + migration strategy + seed data design).**

That becomes the first development artifact and the foundation for everything else.
