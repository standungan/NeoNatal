# Neonatal Care — Backend (FastAPI)

REST API for the Neonatal Care System: authentication, role-based access control, baby & incubator management, vital-sign monitoring, parent-involvement tracking, reporting (incl. PDF), and audit logging.

→ See the [root README](../README.md) for the full-stack overview and architecture.

---

## Tech Stack

| Concern | Choice |
|---|---|
| Framework | FastAPI (async) |
| ORM | SQLAlchemy 2.0 (async) + Alembic |
| Validation | Pydantic v2 |
| Auth | JWT (python-jose), bcrypt via Passlib |
| Database | PostgreSQL (asyncpg driver) |
| Storage | Local filesystem (S3-ready) |

---

## Architecture

A clean layered design — each request flows top-down, each layer depends only on the one below:

```
api/v1/        HTTP routing, dependency injection, RBAC guards
   │
services/      business logic, score/warning calculation, audit hooks
   │
repositories/  data access (SQLAlchemy queries)
   │
models/        ORM entities  ·  schemas/ Pydantic request/response models
```

`core/` holds cross-cutting concerns: `config.py` (settings), `security.py` (hashing + JWT), `database.py` (async session).

```
app/
├── api/v1/        auth, users, incubators, babies, monitoring,
│                  involvement, reports, dashboard, audit
├── core/          config · security · database
├── models/        user, incubator, baby, parent, assignment,
│                  monitoring, involvement, audit
├── schemas/       pydantic models per domain
├── services/      one module per domain + audit_service, storage_service
├── repositories/  data-access per aggregate
└── main.py        app factory, CORS, static /uploads, router mounts
```

---

## Setup

### Prerequisites
- Python 3.12+
- PostgreSQL 14+

### Install
```bash
python -m venv venv
venv\Scripts\activate          # Windows  (source venv/bin/activate on *nix)
pip install -r requirements.txt
```

### Database
```bash
createdb neonatal
psql -d neonatal -f database/schema.sql
psql -d neonatal -f database/seed_data.sql
```

### Environment — `backend/.env`
```env
SECRET_KEY=change-me-to-a-long-random-string
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/neonatal
# optional (defaults shown)
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480
STORAGE_BACKEND=local
STORAGE_LOCAL_PATH=./uploads
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5000
```

| Var | Required | Notes |
|---|---|---|
| `SECRET_KEY` | ✅ | JWT signing secret |
| `DATABASE_URL` | ✅ | Must use the `postgresql+asyncpg://` scheme |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | — | Default `480` (8h) |
| `ALLOWED_ORIGINS` | — | Comma-separated CORS origins (Flutter web, etc.) |

### Run
```bash
uvicorn app.main:app --reload --port 8000
```
- Swagger UI → http://localhost:8000/docs
- ReDoc → http://localhost:8000/redoc
- Health → http://localhost:8000/health

### Migrations (Alembic)
```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

### Tests
```bash
pytest
```

---

## Authentication & RBAC

1. `POST /api/v1/auth/login` returns a JWT containing `sub` (user id), `role`, and `exp`.
2. Clients send it as `Authorization: Bearer <token>`.
3. FastAPI dependencies enforce access per route:

| Guard | Allows |
|---|---|
| `AnyRole` | any authenticated user |
| `PerawatOrAdmin` | nurse + admin (data entry) |
| `AdminOnly` | admin (user mgmt, audit, incubator CRUD) |

> The PDF report endpoint additionally accepts a `?token=` query param, so it can be opened directly in a browser tab where headers can't be set.

All state-changing actions are written to `audit_logs` via `audit_service.log_action`.

---

## API Reference

Base path: `/api/v1` · all routes require a Bearer token except **login**.

### Auth
| Method | Path | Access | Description |
|---|---|---|---|
| POST | `/auth/login` | public | Email/password → JWT |
| GET | `/auth/me` | any | Current user profile |

### Users (admin)
| Method | Path | Description |
|---|---|---|
| GET | `/users` | List users |
| POST | `/users` | Create user |
| GET | `/users/{id}` | Get user |
| PUT | `/users/{id}` | Update (name / active) |
| POST | `/users/{id}/reset-password` | Reset password |
| DELETE | `/users/{id}` | Deactivate user |

### Incubators
| Method | Path | Access | Description |
|---|---|---|---|
| GET | `/incubators` | any | List with current baby |
| GET | `/incubators/available` | any | Empty incubators (for assignment) |
| GET | `/incubators/{id}` | any | Detail |
| POST | `/incubators` | admin | Create |
| PUT | `/incubators/{id}` | admin | Update location/status |

### Babies
| Method | Path | Access | Description |
|---|---|---|---|
| GET | `/babies` | any | List |
| POST | `/babies` | nurse/admin | Register (baby + parent + assignment) |
| GET | `/babies/{id}` | any | Detail (parent, assignment, latest vitals) |
| PUT | `/babies/{id}` | nurse/admin | Update |
| POST | `/babies/{id}/discharge` | nurse/admin | Discharge & free incubator |

### Monitoring
| Method | Path | Access | Description |
|---|---|---|---|
| POST | `/babies/{baby_id}/monitoring` | nurse/admin | Record vitals |
| GET | `/babies/{baby_id}/monitoring` | any | History (paginated) |
| POST | `/monitoring/{monitoring_id}/photo` | nurse/admin | Upload photo (multipart) |

### Parent Involvement
| Method | Path | Access | Description |
|---|---|---|---|
| POST | `/babies/{baby_id}/involvement` | nurse/admin | Log session |
| GET | `/babies/{baby_id}/involvement` | any | History |
| GET | `/babies/{baby_id}/involvement/summary` | any | Aggregated score summary |

### Dashboard / Reports / Audit
| Method | Path | Access | Description |
|---|---|---|---|
| GET | `/dashboard` | any | Stats + incubator grid |
| GET | `/babies/{baby_id}/report` | any | Full report payload |
| GET | `/babies/{baby_id}/report/pdf` | any | PDF (Bearer or `?token=`) |
| GET | `/audit-logs` | admin | Audit trail (`?limit`, `?action`) |

---

## Business Rules

- **Incubator status:** `kosong` · `terisi` · `warning` · `tidak_tersedia`.
- **Vital warning:** out-of-range heart rate / SpO₂ / temperature flags the record `vital_status = "warning"` and can raise the incubator to `warning`.
- **Expression & movement scores:** 1–5 per monitoring entry.
- **Parent involvement score (0–100):** auto-calculated and categorised — `0–25` Rendah · `26–50` Sedang · `51–75` Baik · `76–100` Sangat Baik.

---

## Demo Accounts

Seeded users share the password **`Password123!`**:

| Role | Email |
|---|---|
| Admin | `admin@neonatal.rs` |
| Perawat | `siti.aisyah@neonatal.rs` |
| Dokter | `dr.anisa@neonatal.rs` |
