# API Documentation — Neonatal Care System

REST API served by **FastAPI**. Interactive docs are auto-generated at runtime:

- **Swagger UI:** `GET /docs`
- **ReDoc:** `GET /redoc`
- **OpenAPI JSON:** `GET /openapi.json`

> **👉 Frontend developer?** Start with the [**Getting Started — Frontend Integration Guide**](GETTING_STARTED.md)
> (auth flow, a ready-made typed client, error handling, common recipes). Copy-paste TypeScript types for
> every request & response are in [**api-types.ts**](api-types.ts). This file is the detailed per-endpoint reference.

| | |
|---|---|
| **Base URL** | `http://<host>:8000` (dev) |
| **API prefix** | `/api/v1` |
| **Auth** | JWT Bearer (`Authorization: Bearer <token>`), HS256, 480-min expiry |
| **Content type** | `application/json` (except photo upload = `multipart/form-data`, PDF = `application/pdf`) |
| **Timestamps** | ISO-8601 with timezone |
| **IDs** | UUID v4 |

---

## Table of contents

1. [Authentication & RBAC](#1-authentication--rbac)
2. [Conventions & error format](#2-conventions--error-format)
3. [Auth endpoints](#3-auth)
4. [Users (admin)](#4-users-admin-only)
5. [Incubators](#5-incubators)
6. [Babies](#6-babies)
7. [Monitoring](#7-monitoring)
8. [Parent involvement (Pillar 6)](#8-parent-involvement)
9. [Observation (Monitoring Bayi)](#9-observation-monitoring-bayi)
10. [Menu Aksi (Pillar 8)](#10-menu-aksi-pillar-8)
11. [Dashboard](#11-dashboard)
12. [Reports & PDF](#12-reports--pdf)
13. [Audit logs (admin)](#13-audit-logs-admin-only)
14. [Health & static files](#14-health--static-files)
15. [Endpoint matrix](#15-endpoint-matrix)

---

## 1. Authentication & RBAC

All endpoints except `POST /auth/login` and `GET /health` require a valid JWT.

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

Obtain the token from [`POST /api/v1/auth/login`](#31-login). The token payload is
`{ "sub": <user_id>, "role": <role>, "exp": <unix-ts> }`.

**Roles & guards**

| Role | Guard name | Capability summary |
|---|---|---|
| `admin` | `AdminOnly` | User management, audit log, incubator CRUD; also inherits nurse data-entry rights |
| `perawat` (nurse) | `PerawatOrAdmin` | Baby registration, monitoring, involvement, photo upload, discharge |
| `dokter` (doctor) | `AnyRole` (read) | Read dashboards, babies, reports, PDF export |

A request with a valid token but insufficient role receives **403**. The guard runs before the
handler, so unauthorized calls never reach the database.

---

## 2. Conventions & error format

### HTTP status codes

| Code | Meaning |
|---|---|
| `200 OK` | Successful GET/PUT/POST returning a body |
| `201 Created` | Resource created |
| `204 No Content` | Success, no body (reset password, deactivate, discharge) |
| `401 Unauthorized` | Missing/invalid/expired token, or wrong credentials |
| `403 Forbidden` | Authenticated but role not permitted, or inactive account |
| `404 Not Found` | Resource does not exist |
| `409 Conflict` | Resource state conflict (e.g. assigning a baby to an occupied incubator) |
| `422 Unprocessable Entity` | Request body failed validation (Pydantic) |

### Error body

Standard FastAPI error envelope:

```json
{ "detail": "Email atau password salah" }
```

Validation (`422`) errors return the FastAPI field-level structure:

```json
{
  "detail": [
    { "loc": ["body", "email"], "msg": "value is not a valid email address", "type": "value_error" }
  ]
}
```

### Pagination

List endpoints that support it accept `skip` (offset, default `0`) and `limit` query params
(monitoring/involvement default `limit=50`; audit logs default `limit=100`).

### Reading the request/response schemas

In the per-field tables below: **Req?** ✅ = required in the request body, — = optional (may be omitted).
In the JSON response shapes, `"field|null"` means the key is **always present but may be `null`**.
TypeScript equivalents for every shape are in [api-types.ts](api-types.ts).

---

## 3. Auth

### 3.1 Login
`POST /api/v1/auth/login` · **public**

**Request**
```json
{ "email": "perawat@rs.id", "password": "secret123" }
```

**Response `200`**
```json
{
  "access_token": "eyJhbG...",
  "token_type": "bearer",
  "user_id": "6f1c1b2e-...-9a",
  "full_name": "Suster Ani",
  "role": "perawat"
}
```

**Errors:** `401` wrong email/password · `403` inactive account · `422` malformed email.
Side effect: writes a `LOGIN` row to `audit_logs`.

### 3.2 Current user
`GET /api/v1/auth/me` · **any authenticated role**

**Response `200`** — [`UserResponse`](#user-objects):
```json
{
  "id": "6f1c1b2e-...-9a",
  "role": "perawat",
  "email": "perawat@rs.id",
  "full_name": "Suster Ani",
  "is_active": true,
  "created_at": "2026-06-01T08:00:00+00:00"
}
```

---

## 4. Users (admin only)

All endpoints require role `admin`. Every mutation is audit-logged.

### 4.1 List users
`GET /api/v1/users` → `200` `UserResponse[]`

### 4.2 Create user
`POST /api/v1/users` → `201` `UserResponse`

**Request**
```json
{ "role": "dokter", "email": "dokter@rs.id", "password": "secret123", "full_name": "dr. Budi" }
```
`role` ∈ `admin | perawat | dokter`. Password is bcrypt-hashed server-side.

### 4.3 Get user
`GET /api/v1/users/{user_id}` → `200` `UserResponse` · `404` if absent

### 4.4 Update user
`PUT /api/v1/users/{user_id}` → `200` `UserResponse`

**Request** (both fields optional)
```json
{ "full_name": "dr. Budi Santoso", "is_active": false }
```

### 4.5 Reset password
`POST /api/v1/users/{user_id}/reset-password` → `204 No Content`
```json
{ "new_password": "newSecret123" }
```

### 4.6 Deactivate user
`DELETE /api/v1/users/{user_id}` → `204 No Content`
Soft delete — sets `is_active = false`; the user row and its audit trail are retained.

#### User objects
```jsonc
// UserResponse
{ "id": "uuid", "role": "admin|perawat|dokter", "email": "str",
  "full_name": "str", "is_active": true, "created_at": "datetime" }
```

---

## 5. Incubators

### 5.1 List incubators
`GET /api/v1/incubators` · **any role** → `200` `IncubatorDetailResponse[]`
(each item includes `current_baby` when occupied).

### 5.2 List available
`GET /api/v1/incubators/available` · **any role** → `200` `IncubatorResponse[]`
Only `status = "kosong"` units — used when assigning a baby.

### 5.3 Get incubator
`GET /api/v1/incubators/{incubator_id}` · **any role** → `200` `IncubatorDetailResponse`

### 5.4 Create incubator
`POST /api/v1/incubators` · **admin** → `201` `IncubatorResponse`
```json
{ "incubator_no": "INC-05", "location": "Ruang Perinatologi A" }
```

### 5.5 Update incubator
`PUT /api/v1/incubators/{incubator_id}` · **admin** → `200` `IncubatorResponse`
```json
{ "location": "Ruang NICU B", "status": "tidak_tersedia" }
```
`status` ∈ `kosong | terisi | warning | tidak_tersedia` (both fields optional).

#### Incubator objects
```jsonc
// IncubatorResponse
{ "incubator_id": "uuid", "incubator_no": "INC-05", "location": "str|null",
  "status": "kosong", "created_at": "datetime", "updated_at": "datetime" }

// IncubatorDetailResponse = IncubatorResponse + :
{ "current_baby": { "baby_id": "uuid", "baby_name": "str",
                    "birth_date": "datetime|null", "assigned_at": "datetime" } | null }
```

---

## 6. Babies

### 6.1 List babies
`GET /api/v1/babies` · **any role** → `200` `BabyResponse[]`

### 6.2 Register baby
`POST /api/v1/babies` · **perawat / admin** → `201` `BabyDetailResponse`

Creates the **baby + parent (1:1) + incubator assignment** in one call and flips the
incubator to `terisi`.

**Request**
```json
{
  "baby_name": "Bayi Ny. Sari",
  "gender": "perempuan",
  "birth_date": "2026-06-20",
  "birth_weight": 2450.00,
  "birth_length": 47.5,
  "gestational_age": 36,
  "birth_type": "Sectio Caesarea",
  "clinical_notes": "Prematur ringan",
  "parent": {
    "mother_name": "Ny. Sari",
    "father_name": "Tn. Joko",
    "mother_phone": "0812xxxxxxx",
    "mother_medical_history": "Hipertensi gestasional",
    "birth_history": "...",
    "delivery_history": "...",
    "additional_notes": "..."
  },
  "incubator_id": "0a9b8c7d-6e5f-4a3b-2c1d-9e8f7a6b5c4d"
}
```

| Field | Type | Req? | Notes |
|---|---|:--:|---|
| `baby_name` | string | ✅ | |
| `gender` | enum | ✅ | `laki_laki` \| `perempuan` |
| `birth_date` | string `YYYY-MM-DD` | ✅ | |
| `birth_weight` | number | — | grams |
| `birth_length` | number | — | cm |
| `gestational_age` | number | — | weeks |
| `birth_type` | string | — | e.g. "Sectio Caesarea" |
| `clinical_notes` | string | — | |
| `parent` | object | ✅ | object required; **all its fields optional** |
| `incubator_id` | UUID | ✅ | must reference a `kosong` incubator |

**Errors:** `404` incubator not found · `409` incubator not `kosong` / already occupied · `422` validation.

### 6.3 Get baby
`GET /api/v1/babies/{baby_id}` · **any role** → `200` `BabyDetailResponse`
Includes `age_in_days`, `parent`, `current_assignment`, and `latest_vitals`.

### 6.4 Update baby
`PUT /api/v1/babies/{baby_id}` · **perawat / admin** → `200` `BabyDetailResponse`
```json
{ "baby_name": "...", "clinical_notes": "...", "birth_weight": 2500.00 }
```
(all optional)

### 6.5 Discharge baby
`POST /api/v1/babies/{baby_id}/discharge` · **perawat / admin** → `204 No Content`
Closes the active assignment (`status=discharged`, sets `discharged_at`), frees the incubator
(`kosong`), and sets the baby `is_active=false`.

#### Baby objects
```jsonc
// BabyResponse
{ "baby_id":"uuid","baby_name":"str","gender":"laki_laki|perempuan","birth_date":"date",
  "birth_weight":"num|null","birth_length":"num|null","gestational_age":"int|null",
  "birth_type":"str|null","clinical_notes":"str|null","is_active":true,"created_at":"datetime" }

// BabyDetailResponse = BabyResponse + :
{ "age_in_days": 6,
  "parent": { /* ParentResponse */ } | null,
  "current_assignment": { "assignment_id":"uuid","incubator_id":"uuid","incubator_no":"str",
                          "location":"str|null","assigned_at":"datetime","assigned_by_name":"str|null" } | null,
  "latest_vitals": { /* MonitoringSummary, incl. vital_status */ } | null }
```

---

## 7. Monitoring

Vitals + comfort scores per observation. Implements **IFCDC 8-pillar** fields.

### 7.1 Create monitoring record
`POST /api/v1/babies/{baby_id}/monitoring` · **perawat / admin** → `201` `MonitoringResponse`

**Request** (all vital fields optional; `observation_time` required)
```json
{
  "observation_time": "2026-06-26T09:30:00+07:00",
  "suhu_bayi": 36.8,
  "suhu_inkubator": 33.0,
  "kelembapan_inkubator": 60.0,
  "heart_rate": 140,
  "respiratory_rate": 48,
  "spo2": 97.0,
  "expression_score": 4,
  "movement_score": 3,
  "pain_score": 1,
  "sleep_duration_min": 120,
  "sleep_quality": 4,
  "agitation_episodes": 0,
  "catatan": "Stabil"
}
```

| Field | Type | Req? | Range / unit |
|---|---|:--:|---|
| `observation_time` | string (ISO-8601) | ✅ | when the reading was taken |
| `suhu_bayi` | number | — | °C |
| `suhu_inkubator` | number | — | °C |
| `kelembapan_inkubator` | number | — | % RH |
| `heart_rate` | number | — | bpm |
| `respiratory_rate` | number | — | breaths/min |
| `spo2` | number | — | % |
| `expression_score` | number | — | 1–5 |
| `movement_score` | number | — | 1–5 |
| `pain_score` | number | — | 0–7 (NIPS) |
| `sleep_duration_min` | number | — | minutes |
| `sleep_quality` | number | — | 1–5 |
| `agitation_episodes` | number | — | count |
| `catatan` | string | — | free text |

Only `observation_time` is required; send whichever vitals were measured.
**Validation:** `expression_score`, `movement_score`, `sleep_quality` ∈ `[1,5]`;
`pain_score` ∈ `[0,7]` → else `422`.

**Side effects:** the service computes `vital_status` (see table) and updates the assigned
incubator to `warning` or `terisi`. Writes a `CREATE` audit row.

**Derived `vital_status` thresholds** — any breach ⇒ `"warning"`, else `"normal"`:

| Vital | Normal range |
|---|---|
| `heart_rate` | 100–160 bpm |
| `respiratory_rate` | 40–60 breaths/min |
| `spo2` | ≥ 93 % |
| `suhu_bayi` | 36.0–37.5 °C |
| `pain_score` | < 4 |

> `vital_status` is **computed at read time, never stored**.

### 7.2 List monitoring records
`GET /api/v1/babies/{baby_id}/monitoring?skip=0&limit=50` · **any role** → `200` `MonitoringResponse[]`
Ordered newest first.

### 7.3 Upload photo
`POST /api/v1/monitoring/{monitoring_id}/photo` · **perawat / admin** · `multipart/form-data`
→ `200` `PhotoUploadResponse`

Form field: `file` (image). Stored under `/uploads` (local; S3-pluggable) and served statically.
```json
{ "monitoring_id": "uuid", "foto_url": "/uploads/<baby_id>/<monitoring_id>.jpg" }
```
`404` if the monitoring record does not exist.

#### Monitoring object
```jsonc
// MonitoringResponse
{ "monitoring_id":"uuid","baby_id":"uuid","recorded_by":"uuid","recorder_name":"str|null",
  "observation_time":"datetime","suhu_bayi":"num|null","suhu_inkubator":"num|null",
  "kelembapan_inkubator":"num|null","heart_rate":"int|null","respiratory_rate":"int|null",
  "spo2":"num|null","expression_score":"int|null","movement_score":"int|null","pain_score":"int|null",
  "sleep_duration_min":"int|null","sleep_quality":"int|null","agitation_episodes":"int|null",
  "catatan":"str|null","foto_url":"str|null","vital_status":"normal|warning","created_at":"datetime" }
```

---

## 8. Parent involvement

Keterlibatan Orang Tua is **Pillar 6 "Kerjasama dengan Keluarga"** of the 8-pillar instrument
(see [§9 Observation](#9-observation-monitoring-bayi)): **6 items**, each scored **0–3**, stored as a JSONB
`scores` map. The server computes `total_score` (0–18), `percentage`, a `category` band, a per-item
breakdown, and `alarms`.

> **Scoring per item:** 3 = sesuai standar · 2 = penyimpangan ringan · 1 = sedang · 0 = berat.
> **Percentage:** `round( total_score / 18 × 100, 1 )`.
> **Category:** ≥85% `Sangat Baik` · 70–84% `Baik` · 55–69% `Cukup` · 40–54% `Kurang` · <40% `Sangat Kurang`.
> **Alarm:** any item scored 0 or 1.
> `durasi_menyusui`, `durasi_interaksi`, `kondisi_bayi`, `catatan` are optional context, **not** part of the score.

### 8.1 Catalog
`GET /api/v1/involvement/catalog` · **any role** → `200` `InvolvementCatalog`

The fixed 6-item catalog (source of truth for the form). Item codes are stable (`keluarga_1..6`).
```json
{
  "key": "keluarga",
  "label": "Kerjasama dengan Keluarga",
  "items": [
    { "item_code": "keluarga_1", "text": "Ibu memberikan ASI/perah ASI" },
    { "item_code": "keluarga_2", "text": "Keluarga memahami kondisi bayi" },
    { "item_code": "keluarga_3", "text": "Keluarga terlibat dalam PMK" },
    { "item_code": "keluarga_4", "text": "Keluarga membantu perawatan dasar" },
    { "item_code": "keluarga_5", "text": "Keluarga mengikuti edukasi" },
    { "item_code": "keluarga_6", "text": "Keluarga memahami perawatan di rumah" }
  ],
  "total_items": 6,
  "max_total": 18
}
```

### 8.2 Create involvement record
`POST /api/v1/babies/{baby_id}/involvement` · **perawat / admin** → `201` `InvolvementResponse`

**Request** (`observation_time` + `scores` required; the rest optional)
```json
{
  "observation_time": "2026-07-08T10:00:00+07:00",
  "scores": {
    "keluarga_1": 3, "keluarga_2": 2, "keluarga_3": 1,
    "keluarga_4": 3, "keluarga_5": 2, "keluarga_6": 0
  },
  "durasi_menyusui": 25,
  "durasi_interaksi": 40,
  "kondisi_bayi": "Tenang",
  "catatan": "Ibu aktif; edukasi PMK dilanjutkan"
}
```
| Field | Type | Req? | Range / unit |
|---|---|:--:|---|
| `observation_time` | string (ISO-8601) | ✅ | when the assessment was done |
| `scores` | object `{ item_code: number }` | ✅ | keys `keluarga_1..6`; each value **0–3** |
| `durasi_menyusui` | number | — | minutes (informational) |
| `durasi_interaksi` | number | — | minutes (informational) |
| `kondisi_bayi` | string | — | e.g. `Tenang` / `Aktif` |
| `catatan` | string | — | |

Omitted items count as 0. **Validation:** each score ∈ `[0,3]`; durations ≥ 0 → else `422`.
`404` if the baby does not exist. The computed `percentage`, `category`, and alarm count are written into the audit `details`.

**Response** `InvolvementResponse` (server computes `total`, `percentage`, `category`, `items`, `alarms`):
```json
{
  "involvement_id": "…", "baby_id": "…", "recorded_by": "…", "recorder_name": "Siti Aisyah",
  "observation_time": "2026-07-08T10:00:00+07:00",
  "scores": { "keluarga_1": 3, "keluarga_2": 2, "keluarga_3": 1, "keluarga_4": 3, "keluarga_5": 2, "keluarga_6": 0 },
  "catatan": "Ibu aktif; edukasi PMK dilanjutkan",
  "durasi_menyusui": 25, "durasi_interaksi": 40, "kondisi_bayi": "Tenang",
  "total_score": 11, "max_total": 18, "percentage": 61.1, "category": "Cukup",
  "items": [
    { "item_code": "keluarga_1", "text": "Ibu memberikan ASI/perah ASI", "score": 3, "max": 3, "percentage": 100.0 },
    { "item_code": "keluarga_3", "text": "Keluarga terlibat dalam PMK", "score": 1, "max": 3, "percentage": 33.3 }
  ],
  "alarms": [
    { "item_code": "keluarga_3", "text": "Keluarga terlibat dalam PMK", "score": 1 },
    { "item_code": "keluarga_6", "text": "Keluarga memahami perawatan di rumah", "score": 0 }
  ],
  "created_at": "2026-07-08T10:00:05+07:00"
}
```

### 8.3 List involvement records
`GET /api/v1/babies/{baby_id}/involvement?skip=0&limit=50` · **any role** → `200` `InvolvementResponse[]`

### 8.4 Involvement summary
`GET /api/v1/babies/{baby_id}/involvement/summary` · **any role** → `200` `InvolvementSummary`
```json
{
  "total_sessions": 4,
  "avg_percentage": 77.8,
  "latest_percentage": 88.9,
  "latest_category": "Sangat Baik",
  "avg_durasi_menyusui": 17.6,
  "avg_durasi_interaksi": 37.8
}
```

#### Involvement object
```jsonc
// InvolvementResponse
{ "involvement_id":"uuid","baby_id":"uuid","recorded_by":"uuid","recorder_name":"str|null",
  "observation_time":"datetime","scores":{"keluarga_1":0,"…":3},"catatan":"str|null",
  "durasi_menyusui":"int|null","durasi_interaksi":"int|null","kondisi_bayi":"str|null",
  "total_score":11,"max_total":18,"percentage":61.1,"category":"Cukup",
  "items":[{"item_code":"keluarga_1","text":"…","score":3,"max":3,"percentage":100.0}],
  "alarms":[{"item_code":"keluarga_6","text":"…","score":0}],
  "created_at":"datetime" }
```

---

## 9. Observation (Monitoring Bayi)

The **Instrumen Observasi Perawatan Bayi Prematur** — a structured premature-baby care assessment.
Currently **6 pillars / 42 items**, each scored **0–3**, stored as a JSONB `scores` map. The server
computes `total_score` (0–126), `percentage`, a `category` band, per-pillar scores, and `alarms`.

> **Scoring per item:** 3 = sesuai standar · 2 = ringan · 1 = sedang · 0 = berat.
> **Percentage:** `round( total_score / 126 × 100, 1 )`. Same 5 `category` bands as §8.
> **Alarm:** any item scored 0 or 1. **Side effect:** any item scored **0** flips the baby's active incubator to `warning`.
> Two pillars of the original 8-pillar instrument are served as their own modules: "Kerjasama dengan Keluarga" → [Parent involvement](#8-parent-involvement) (§8); "Kolaborasi Interprofesional" → [Menu Aksi](#10-menu-aksi-pillar-8) (§10).

### 9.1 Catalog
`GET /api/v1/observation/catalog` · **any role** → `200` `ObservationCatalog`

The fixed pillar/item catalog (source of truth for the form). Item codes are stable, `{pillar_key}_{n}`.
```json
{
  "pillars": [
    { "key": "tidur", "label": "Menjaga Masa Tidur Bayi",
      "items": [ { "item_code": "tidur_1", "text": "Bayi memperoleh periode tidur tanpa gangguan minimal 60 menit" } ] },
    { "key": "nyeri", "label": "Manajemen Stres dan Nyeri", "items": [] }
  ],
  "total_items": 42,
  "max_total": 126
}
```
Pillars & item counts: `tidur`(8) · `nyeri`(6) · `posisi`(6) · `kulit`(8) · `nutrisi`(8) · `lingkungan`(6).

### 9.2 Create observation
`POST /api/v1/babies/{baby_id}/observation` · **perawat / admin** → `201` `ObservationResponse`

**Request** (`observation_time` + `scores` required)
```json
{
  "observation_time": "2026-07-08T09:00:00+07:00",
  "scores": { "tidur_1": 3, "tidur_2": 2, "nyeri_1": 3, "kulit_2": 0 },
  "catatan": "Bayi tenang, humidity sesuai"
}
```
| Field | Type | Req? | Range |
|---|---|:--:|---|
| `observation_time` | string (ISO-8601) | ✅ | |
| `scores` | object `{ item_code: number }` | ✅ | each value **0–3** |
| `catatan` | string | — | |

Omitted items count as 0. **Validation:** each score ∈ `[0,3]` → else `422`. `404` if the baby does not exist.

**Response** `ObservationResponse`:
```jsonc
{ "observation_id":"uuid","baby_id":"uuid","recorded_by":"uuid","recorder_name":"str|null",
  "observation_time":"datetime","scores":{"tidur_1":3,"…":0},"catatan":"str|null",
  "total_score":100,"max_total":126,"percentage":79.4,"category":"Baik",
  "pillars":[{"key":"tidur","label":"Menjaga Masa Tidur Bayi","score":20,"max":24,"percentage":83.3}],
  "alarms":[{"item_code":"kulit_2","text":"…","pillar_label":"Perlindungan Kulit","score":0}],
  "created_at":"datetime" }
```

### 9.3 List observations
`GET /api/v1/babies/{baby_id}/observation?skip=0&limit=50` · **any role** → `200` `ObservationResponse[]`

---

## 10. Menu Aksi (Pillar 8)

**Kolaborasi Interprofesional** — Pillar 8 of the 8-pillar instrument, pulled out of Monitoring Bayi
(§9) into its own module: **6 items**, each scored **0–3**, stored as a JSONB `scores` map. The server
computes `total_score` (0–18), `percentage`, a `category` band, per-item breakdown, and `alarms`.

> **Percentage:** `round( total_score / 18 × 100, 1 )`. Same 5 `category` bands as §8.
> **Alarm:** any item scored 0 or 1. No incubator side effect (collaboration is not a vital sign).

### 10.1 Catalog
`GET /api/v1/aksi/catalog` · **any role** → `200` `AksiCatalog`
```json
{
  "key": "kolaborasi",
  "label": "Kolaborasi Interprofesional",
  "items": [
    { "item_code": "kolaborasi_1", "text": "Catatan CPPT lengkap" },
    { "item_code": "kolaborasi_2", "text": "SBAR dilakukan saat handover" }
  ],
  "total_items": 6,
  "max_total": 18
}
```
Items `kolaborasi_1..6`: CPPT lengkap · SBAR handover · instruksi dokter · lapor perubahan kondisi · kolaborasi dokter-perawat · dokumentasi tindakan.

### 10.2 Create aksi
`POST /api/v1/babies/{baby_id}/aksi` · **perawat / admin** → `201` `AksiResponse`

**Request** (`observation_time` + `scores` required)
```json
{
  "observation_time": "2026-07-10T13:00:00+07:00",
  "scores": { "kolaborasi_1": 3, "kolaborasi_2": 3, "kolaborasi_4": 1 },
  "catatan": "Handover lengkap, SBAR jelas"
}
```
| Field | Type | Req? | Range |
|---|---|:--:|---|
| `observation_time` | string (ISO-8601) | ✅ | |
| `scores` | object `{ item_code: number }` | ✅ | each value **0–3** |
| `catatan` | string | — | |

Omitted items count as 0. **Validation:** each score ∈ `[0,3]` → else `422`. `404` if the baby does not exist.

**Response** `AksiResponse`:
```jsonc
{ "aksi_id":"uuid","baby_id":"uuid","recorded_by":"uuid","recorder_name":"str|null",
  "observation_time":"datetime","scores":{"kolaborasi_1":3,"…":0},"catatan":"str|null",
  "total_score":12,"max_total":18,"percentage":66.7,"category":"Cukup",
  "items":[{"item_code":"kolaborasi_1","text":"Catatan CPPT lengkap","score":3,"max":3,"percentage":100.0}],
  "alarms":[{"item_code":"kolaborasi_4","text":"…","score":1}],
  "created_at":"datetime" }
```

### 10.3 List aksi
`GET /api/v1/babies/{baby_id}/aksi?skip=0&limit=50` · **any role** → `200` `AksiResponse[]`

### 10.4 Aksi summary
`GET /api/v1/babies/{baby_id}/aksi/summary` · **any role** → `200` `AksiSummary`
```json
{ "total_sessions": 5, "avg_percentage": 78.9, "latest_percentage": 66.7, "latest_category": "Cukup" }
```

---

## 11. Dashboard

### 10.1 Get dashboard
`GET /api/v1/dashboard` · **any role** → `200` `DashboardResponse`

Aggregate incubator occupancy stats plus a per-incubator board with current baby and latest vitals.
```json
{
  "stats": { "total": 10, "terisi": 6, "kosong": 3, "warning": 1, "tidak_tersedia": 0 },
  "incubators": [
    {
      "incubator_id": "uuid", "incubator_no": "INC-01", "location": "Perinatologi A",
      "status": "terisi",
      "current_baby": { "baby_id":"uuid","baby_name":"Bayi Ny. Sari","age_in_days":6,
                        "birth_weight":2450.00,"assigned_at":"datetime" },
      "latest_vitals": { "suhu_bayi":36.8,"heart_rate":140,"spo2":97.0,
                         "observation_time":"datetime","vital_status":"normal" }
    }
  ]
}
```

---

## 12. Reports & PDF

### 11.1 Baby report (JSON)
`GET /api/v1/babies/{baby_id}/report` · **any role** → `200` `BabyReportResponse`
```jsonc
{ "baby": { /* BabyDetailResponse */ },
  "monitoring_history":  [ /* MonitoringResponse[] */ ],
  "involvement_history": [ /* InvolvementResponse[] */ ],
  "involvement_summary": { /* InvolvementSummary */ },
  "generated_at": "datetime" }
```

### 11.2 Baby report (PDF)
`GET /api/v1/babies/{baby_id}/report/pdf` → `200` `application/pdf`

**Dual authentication** — supply *either*:
- `Authorization: Bearer <token>` header (API clients), **or**
- `?token=<jwt>` query param (browser download via `url_launcher`, which cannot set headers).

Returns the PDF as an attachment: `Content-Disposition: attachment; filename="laporan_<baby_name>.pdf"`.
`401` if neither token is valid.

---

## 13. Audit logs (admin only)

### 12.1 List audit logs
`GET /api/v1/audit-logs` · **admin** → `200` `AuditLogResponse[]`

**Query params:** `skip` (default 0), `limit` (default 100), `action` (optional exact-match filter,
e.g. `LOGIN`, `CREATE`, `UPDATE`, `UPLOAD_PHOTO`).

```json
[
  {
    "log_id": "uuid",
    "user_id": "uuid|null",
    "user_name": "Suster Ani",
    "action": "CREATE",
    "table_name": "monitoring_records",
    "record_id": "uuid|null",
    "ip_address": "203.0.113.5",
    "details": { "skor": 75, "kategori": "Baik" },
    "created_at": "datetime"
  }
]
```

**Logged actions** include `LOGIN`, `CREATE`, `UPDATE`, `RESET_PASSWORD`, `DEACTIVATE`,
`UPLOAD_PHOTO`, `DISCHARGE` (varies by endpoint).

---

## 14. Health & static files

| Endpoint | Auth | Description |
|---|---|---|
| `GET /health` | public | `{ "status": "ok", "version": "1.0.0" }` |
| `GET /uploads/<path>` | public (static) | Uploaded monitoring photos (FastAPI `StaticFiles` mount) |
| `GET /docs` · `/redoc` · `/openapi.json` | public | Interactive / machine-readable API specs |

---

## 15. Endpoint matrix

| Method | Path | Role | Success |
|---|---|---|---|
| POST | `/api/v1/auth/login` | public | 200 |
| GET | `/api/v1/auth/me` | any | 200 |
| GET | `/api/v1/users` | admin | 200 |
| POST | `/api/v1/users` | admin | 201 |
| GET | `/api/v1/users/{id}` | admin | 200 |
| PUT | `/api/v1/users/{id}` | admin | 200 |
| POST | `/api/v1/users/{id}/reset-password` | admin | 204 |
| DELETE | `/api/v1/users/{id}` | admin | 204 |
| GET | `/api/v1/incubators` | any | 200 |
| GET | `/api/v1/incubators/available` | any | 200 |
| GET | `/api/v1/incubators/{id}` | any | 200 |
| POST | `/api/v1/incubators` | admin | 201 |
| PUT | `/api/v1/incubators/{id}` | admin | 200 |
| GET | `/api/v1/babies` | any | 200 |
| POST | `/api/v1/babies` | perawat/admin | 201 |
| GET | `/api/v1/babies/{id}` | any | 200 |
| PUT | `/api/v1/babies/{id}` | perawat/admin | 200 |
| POST | `/api/v1/babies/{id}/discharge` | perawat/admin | 204 |
| POST | `/api/v1/babies/{id}/monitoring` | perawat/admin | 201 |
| GET | `/api/v1/babies/{id}/monitoring` | any | 200 |
| POST | `/api/v1/monitoring/{id}/photo` | perawat/admin | 200 |
| GET | `/api/v1/involvement/catalog` | any | 200 |
| POST | `/api/v1/babies/{id}/involvement` | perawat/admin | 201 |
| GET | `/api/v1/babies/{id}/involvement` | any | 200 |
| GET | `/api/v1/babies/{id}/involvement/summary` | any | 200 |
| GET | `/api/v1/observation/catalog` | any | 200 |
| POST | `/api/v1/babies/{id}/observation` | perawat/admin | 201 |
| GET | `/api/v1/babies/{id}/observation` | any | 200 |
| GET | `/api/v1/aksi/catalog` | any | 200 |
| POST | `/api/v1/babies/{id}/aksi` | perawat/admin | 201 |
| GET | `/api/v1/babies/{id}/aksi` | any | 200 |
| GET | `/api/v1/babies/{id}/aksi/summary` | any | 200 |
| GET | `/api/v1/dashboard` | any | 200 |
| GET | `/api/v1/babies/{id}/report` | any | 200 |
| GET | `/api/v1/babies/{id}/report/pdf` | any (header or `?token=`) | 200 (PDF) |
| GET | `/api/v1/audit-logs` | admin | 200 |
| GET | `/health` | public | 200 |
