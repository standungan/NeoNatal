# Sequence Diagrams — Neonatal Care System

API request flows for the core scenarios. Each diagram traces a request through the
**Router → Dependency (auth/RBAC) → Service → Repository → PostgreSQL** layers described in
[COMPONENT_DIAGRAM.md](COMPONENT_DIAGRAM.md).

> **📊 How to view the diagrams.** They're [Mermaid](https://mermaid.js.org/) sequence diagrams — they
> render automatically on **GitHub** and in **VS Code** (with the *Markdown Preview Mermaid Support*
> extension → open Preview). If you only see raw `sequenceDiagram` text, paste the code block into
> <https://mermaid.live>. Notes and tables under each diagram summarize the flow in plain text.

---

## 1. Authentication — Login & authenticated request

`POST /api/v1/auth/login` issues a JWT; every subsequent call is verified by `get_current_user`.

```mermaid
sequenceDiagram
    autonumber
    actor Nurse as Client (Flutter / Web)
    participant API as auth.py (router)
    participant Svc as auth_service.login()
    participant Repo as UserRepository
    participant Sec as core.security
    participant Audit as audit_service
    participant DB as PostgreSQL

    Nurse->>API: POST /auth/login {email, password}
    API->>Svc: login(data, ip)
    Svc->>Repo: get_by_email(email)
    Repo->>DB: SELECT * FROM users WHERE email=?
    DB-->>Repo: user row (or none)
    Repo-->>Svc: User | None

    alt user missing OR bad password
        Svc->>Sec: verify_password(plain, hash)
        Sec-->>Svc: False
        Svc-->>Nurse: 401 "Email atau password salah"
    else inactive account
        Svc-->>Nurse: 403 "Akun tidak aktif"
    else valid credentials
        Svc->>Audit: log_action(LOGIN, user_id, ip)
        Audit->>DB: INSERT INTO audit_logs
        Svc->>Sec: create_access_token(user_id, role)
        Sec-->>Svc: signed JWT (HS256, exp=480 min)
        Svc-->>Nurse: 200 {access_token, user_id, full_name, role}
    end

    note over Nurse,DB: Subsequent authenticated request
    Nurse->>API: GET /api/v1/... (Authorization: Bearer <jwt>)
    API->>API: get_current_user — decode JWT, load User, check is_active
    alt token invalid / user inactive
        API-->>Nurse: 401
    else ok
        API-->>Nurse: 200 (handler result)
    end
```

> **Web (Next.js) variant:** the browser never holds the token. `app/api/auth/login` calls FastAPI,
> then stores the JWT in an **httpOnly cookie** (`nc_token`). Later calls go to same-origin
> `/api/v1/[...path]`, which reads the cookie and re-attaches the `Bearer` header server-side.

---

## 2. Create monitoring record — with vital-status evaluation & incubator side effect

`POST /api/v1/babies/{baby_id}/monitoring` — the richest flow. A `perawat`/`admin` submits vitals;
the service derives a `normal`/`warning` status and **propagates it to the incubator**.

```mermaid
sequenceDiagram
    autonumber
    actor Nurse
    participant API as monitoring.py
    participant Dep as deps.PerawatOrAdmin
    participant Svc as monitoring_service
    participant MRepo as MonitoringRepository
    participant ARepo as AssignmentRepository
    participant IRepo as IncubatorRepository
    participant Audit as audit_service
    participant DB as PostgreSQL

    Nurse->>API: POST /babies/{id}/monitoring {vitals...}
    API->>Dep: resolve current_user (role in {perawat, admin})
    alt role not allowed
        Dep-->>Nurse: 403 "Akses tidak diizinkan untuk role ini"
    else allowed
        API->>Svc: create_monitoring(baby_id, data, actor_id, ip)
        Svc->>MRepo: create(MonitoringRecord)
        MRepo->>DB: INSERT INTO monitoring_records
        DB-->>MRepo: row

        Svc->>Svc: _check_vital_status(HR, SpO2, temp, RR, pain)
        note right of Svc: thresholds — HR 100-160, RR 40-60,<br/>SpO2 ≥ 93, temp 36.0-37.5, pain < 4

        Svc->>ARepo: get_active_by_baby(baby_id)
        ARepo->>DB: SELECT active assignment + incubator
        DB-->>ARepo: assignment | none
        opt has active assignment
            alt vital_status == warning
                Svc->>IRepo: update incubator.status = "warning"
            else normal
                Svc->>IRepo: update incubator.status = "terisi"
            end
            IRepo->>DB: UPDATE incubators (only if status changed)
        end

        Svc->>Audit: log_action(CREATE, monitoring_records, record_id, ip)
        Audit->>DB: INSERT INTO audit_logs
        Svc->>MRepo: get_by_id() (reload with recorder)
        MRepo->>DB: SELECT ... JOIN users
        Svc-->>Nurse: 201 MonitoringResponse {..., vital_status}
    end
```

**Vital thresholds** (`monitoring_service._check_vital_status`): any breach → `warning`.

| Vital | Normal range |
|---|---|
| Heart rate | 100–160 bpm |
| Respiratory rate | 40–60 breaths/min |
| SpO₂ | ≥ 93 % |
| Baby temperature | 36.0–37.5 °C |
| Pain score (NIPS) | < 4 |

`vital_status` is **computed, never stored** — recomputed on every read so threshold tuning needs no migration.

---

## 3. Register baby — baby + parent + incubator assignment (one transaction)

`POST /api/v1/babies` creates three related rows together and flips the incubator to `terisi`.

```mermaid
sequenceDiagram
    autonumber
    actor Nurse
    participant API as babies.py
    participant Dep as deps.PerawatOrAdmin
    participant Svc as baby_service.register_baby()
    participant BRepo as BabyRepository
    participant ARepo as AssignmentRepository
    participant IRepo as IncubatorRepository
    participant Audit as audit_service
    participant DB as PostgreSQL

    Nurse->>API: POST /babies {baby, parent, incubator_id}
    API->>Dep: require role perawat|admin
    API->>Svc: register_baby(data, actor_id, ip)
    Svc->>BRepo: create Baby + Parent (1:1)
    BRepo->>DB: INSERT babies, INSERT parents
    Svc->>ARepo: create assignment(status=active, assigned_by=actor)
    ARepo->>DB: INSERT baby_incubator_assignments
    Svc->>IRepo: set incubator.status = "terisi"
    IRepo->>DB: UPDATE incubators
    Svc->>Audit: log_action(CREATE, babies, baby_id, ip)
    Audit->>DB: INSERT audit_logs
    Svc-->>Nurse: 201 BabyDetailResponse {baby, parent, current_assignment, age_in_days}
```

---

## 4. Parent involvement — Pillar 6 scoring

`POST /api/v1/babies/{baby_id}/involvement` — Keterlibatan Orang Tua = **Pillar 6 "Kerjasama dengan
Keluarga"** (6 items, each 0–3). The service computes `total_score` (0–18), `percentage`, and a
`category` band from the catalog, plus a per-item breakdown and alarms.

```mermaid
sequenceDiagram
    autonumber
    actor Nurse
    participant API as involvement.py
    participant Svc as involvement_service
    participant Repo as InvolvementRepository
    participant Audit as audit_service
    participant DB as PostgreSQL

    Nurse->>API: POST /babies/{id}/involvement {scores {keluarga_1..6: 0-3}, context}
    API->>Svc: create_involvement(baby_id, data, actor_id, ip)
    Svc->>Svc: total = sum(scores); percentage = round(total / 18 * 100, 1)
    Svc->>Svc: category band; alarms = items scored 0-1
    Svc->>Repo: create(record incl. scores, total_score, percentage, category)
    Repo->>DB: INSERT parent_involvement_records
    Svc->>Audit: log_action(CREATE, parent_involvement_records, id, ip)
    Audit->>DB: INSERT audit_logs
    Svc-->>Nurse: 201 InvolvementResponse {percentage, category, items[], alarms[]}
```

**Category bands (both instruments):** ≥85% Sangat Baik · 70–84% Baik · 55–69% Cukup · 40–54% Kurang · <40% Sangat Kurang.

---

## 5. Baby report PDF — dual auth (header **or** `?token=`)

`GET /api/v1/babies/{baby_id}/report/pdf` supports a query-param token because browser download
launchers (`url_launcher`) cannot set an `Authorization` header.

```mermaid
sequenceDiagram
    autonumber
    actor User as Doctor / Nurse
    participant API as reports.py
    participant Sec as core.security
    participant URepo as UserRepository
    participant RSvc as report_service
    participant PSvc as pdf_service
    participant DB as PostgreSQL

    User->>API: GET /babies/{id}/report/pdf  (Bearer header OR ?token=)
    API->>API: pick raw_token (header credentials → else query token)
    alt no token
        API-->>User: 401 "Not authenticated"
    else token present
        API->>Sec: decode_access_token(raw_token)
        Sec-->>API: payload {sub, role} | {}
        alt invalid / user inactive
            API->>URepo: get_by_id(sub)
            URepo->>DB: SELECT user
            API-->>User: 401
        else valid
            API->>RSvc: get_baby_report(baby_id)
            RSvc->>DB: SELECT baby + monitoring + involvement (+ summary)
            RSvc-->>API: BabyReportResponse
            API->>PSvc: generate_pdf(report)
            PSvc-->>API: pdf bytes
            API-->>User: 200 application/pdf<br/>Content-Disposition: attachment; laporan_<name>.pdf
        end
    end
```

---

## 6. Admin — create user (RBAC + audit)

`POST /api/v1/users` is gated to `admin` via the `AdminOnly` dependency; the mutation is audit-logged.

```mermaid
sequenceDiagram
    autonumber
    actor Admin
    participant API as users.py
    participant Dep as deps.AdminOnly
    participant Svc as user_service
    participant Sec as core.security
    participant Repo as UserRepository
    participant Audit as audit_service
    participant DB as PostgreSQL

    Admin->>API: POST /users {role, email, password, full_name}
    API->>Dep: current_user.role == "admin"?
    alt not admin
        Dep-->>Admin: 403
    else admin
        API->>Svc: create_user(data, actor_id, ip)
        Svc->>Sec: hash_password(password)  (bcrypt)
        Svc->>Repo: create(User)
        Repo->>DB: INSERT users
        Svc->>Audit: log_action(CREATE, users, new_id, ip)
        Audit->>DB: INSERT audit_logs
        Svc-->>Admin: 201 UserResponse
    end
```

---

## Cross-cutting notes

- **Every mutating endpoint** (login, create/update/delete, photo upload, discharge) calls
  `audit_service.log_action(...)`, capturing actor, action, table, record id, IP, and a JSON `details`
  payload — see §2.8 of [ERD.md](ERD.md).
- **Role guards** resolve *before* the handler body runs, so an unauthorized caller never reaches the
  service/DB layer. Guards: `AnyRole` (any authenticated), `PerawatOrAdmin`, `AdminOnly`.
- **Client IP** is read from `request.client.host` in the router and threaded through to the audit log.
