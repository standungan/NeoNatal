# Component Diagram — Neonatal Care System

System architecture across the three deployables: **Flutter** (mobile data entry),
**Next.js** (web dashboard), and the **FastAPI** backend over **PostgreSQL**.

> **📊 How to view the diagrams.** They're [Mermaid](https://mermaid.js.org/) and render automatically on
> **GitHub** and in **VS Code** (with the *Markdown Preview Mermaid Support* extension → open Preview). If
> you see only raw `flowchart` text, paste the code block into <https://mermaid.live>. Each diagram is
> followed by a plain-text explanation, so you can follow the architecture without rendering.

---

## 1. High-level system architecture

```mermaid
flowchart TB
    subgraph Clients["Client layer"]
        direction LR
        Mobile["📱 Flutter app<br/>(nurses — data entry)<br/>Bearer JWT in header"]
        Web["💻 Next.js web dashboard<br/>(doctors / admin — read and manage)<br/>Next.js 16 · React 19 · Tailwind v4"]
    end

    subgraph WebBFF["Next.js server (BFF)"]
        direction TB
        Proxy["proxy.ts<br/>route gating — decode JWT,<br/>redirect unauth → /login,<br/>non-admin → away from /admin"]
        AuthRoutes["app/api/auth/*<br/>sets / clears httpOnly cookie nc_token"]
        ApiProxy["app/api/v1/[...path]<br/>injects Bearer server-side,<br/>proxies to FastAPI"]
    end

    subgraph Backend["FastAPI backend (app/)"]
        direction TB
        API["API routers — app/api/v1/*<br/>auth · users · incubators · babies ·<br/>monitoring · involvement · dashboard ·<br/>reports · audit-logs"]
        Deps["Dependencies — app/api/deps.py<br/>get_current_user · require_roles()<br/>AdminOnly / PerawatOrAdmin / AnyRole"]
        Services["Service layer — app/services/*<br/>business rules, instrument + vital-status calc,<br/>PDF generation, audit logging"]
        Repos["Repository layer — app/repositories/*<br/>async SQLAlchemy queries"]
        Core["Core — app/core/*<br/>config · security (JWT, bcrypt) · database"]
    end

    subgraph Data["Persistence and storage"]
        direction LR
        DB[("PostgreSQL<br/>9 tables · Alembic migrations")]
        Files["Local file storage<br/>/uploads (StaticFiles)<br/>→ S3 pluggable"]
    end

    Mobile -->|"HTTPS · Bearer JWT<br/>/api/v1/*"| API
    Web -->|same-origin fetch| Proxy
    Web -->|axios same-origin| ApiProxy
    Proxy --> AuthRoutes
    ApiProxy -->|"Bearer JWT (server-side)"| API

    API --> Deps
    Deps --> Services
    API --> Services
    Services --> Repos
    Services --> Core
    Repos --> Core
    Repos --> DB
    Services -->|save / serve photos| Files
    API -.->|mount /uploads| Files
```

**Two auth strategies, one backend.**

- **Flutter** stores the JWT and sends it as an `Authorization: Bearer …` header on every call.
- **Next.js** uses an **httpOnly-cookie BFF**: the token lives in the `nc_token` cookie (never exposed
  to browser JS). The browser calls same-origin `/api/v1/*`; `app/api/v1/[...path]/route.ts` reads the
  cookie and re-attaches the Bearer when proxying to FastAPI — so there is no CORS exposure and no token
  in client memory.

---

## 2. Backend layered architecture

The backend follows a clean **Router → Service → Repository** layering. Routers never touch the DB
directly; services hold business rules; repositories own all SQLAlchemy.

```mermaid
flowchart LR
    subgraph R["API / Router layer"]
        direction TB
        r1["auth.py"]
        r2["users.py"]
        r3["babies.py"]
        r4["monitoring.py"]
        r5["involvement.py"]
        r6["incubators.py"]
        r7["dashboard.py"]
        r8["reports.py"]
        r9["audit.py"]
    end

    subgraph D["Dependencies (deps.py)"]
        d1["get_current_user()"]
        d2["require_roles()<br/>AdminOnly · PerawatOrAdmin · AnyRole"]
    end

    subgraph S["Service layer"]
        direction TB
        s1["auth_service"]
        s2["user_service"]
        s3["baby_service"]
        s4["monitoring_service<br/>(vital-status thresholds)"]
        s5["involvement_service<br/>(Pillar 6 scoring)"]
        s6["incubator_service"]
        s7["dashboard_service"]
        s8["report_service + pdf_service"]
        s9["audit_service"]
        s10["storage_service"]
        s11["observation_service<br/>(8-pillar scoring)"]
    end

    subgraph Rep["Repository layer"]
        direction TB
        rep1["user_repository"]
        rep2["baby_repository"]
        rep3["monitoring_repository"]
        rep4["involvement_repository"]
        rep5["incubator_repository"]
        rep6["assignment_repository"]
        rep7["audit_repository"]
        rep8["observation_repository"]
    end

    subgraph M["Models / Schemas"]
        m1["SQLAlchemy models<br/>(app/models)"]
        m2["Pydantic schemas<br/>(app/schemas)"]
    end

    DB[("PostgreSQL")]
    FS["/uploads<br/>(local · S3-pluggable)"]

    R --> D
    R --> S
    S --> Rep
    S --> m2
    S -.->|every mutation| s9
    s8 -.-> FS
    s10 --> FS
    Rep --> m1
    Rep --> DB
```

### Layer responsibilities

| Layer | Directory | Responsibility |
|---|---|---|
| **Router** | `app/api/v1/` | HTTP shape only — path/query/body binding, status codes, response models. Declares the role guard it needs. |
| **Dependencies** | `app/api/deps.py` | Decode JWT → load `User`; `require_roles()` factory builds `AdminOnly`, `PerawatOrAdmin`, `AnyRole`. |
| **Service** | `app/services/` | Business logic: instrument scoring (observation + Pillar-6 involvement), vital-status thresholds + incubator-status side effects, PDF rendering, and **audit logging on every mutation**. |
| **Repository** | `app/repositories/` | All async SQLAlchemy queries; the only layer that touches the session/DB. |
| **Core** | `app/core/` | `config` (env settings), `security` (JWT encode/decode, bcrypt), `database` (async engine + `get_db`). |
| **Models / Schemas** | `app/models`, `app/schemas` | ORM entities vs. Pydantic request/response contracts. |

---

## 3. Web dashboard (Next.js) internal components

```mermaid
flowchart TB
    subgraph Browser
        Pages["App Router pages<br/>(app)/dashboard · /incubator/[id]<br/>/baby/[id]/report · /admin/users · /admin/audit-logs · /login"]
        Axios["lib/api.ts<br/>axios → same-origin /api/v1/*"]
        Query["TanStack Query<br/>cache + fetching"]
        Charts["Recharts<br/>vitals trend"]
    end

    subgraph Server["Next.js server runtime"]
        Pxy["proxy.ts (route gating)"]
        AuthH["app/api/auth/login · logout · me"]
        ProxyH["app/api/v1/[...path]"]
    end

    FastAPI["FastAPI /api/v1/*"]

    Pages --> Query --> Axios --> ProxyH
    Pages --> Charts
    Pages -.guarded by.-> Pxy
    Pages --> AuthH
    AuthH -->|"login → set nc_token cookie"| FastAPI
    ProxyH -->|"Bearer from cookie"| FastAPI
```

**Stack:** Next.js 16.2 (App Router, Turbopack) · React 19 · TypeScript · Tailwind v4
(`@theme` in `app/globals.css`) · TanStack Query · Recharts · Manrope font.
Data-entry forms are intentionally **not** in the web app — registration / monitoring /
involvement entry live in the Flutter client; the web dashboard is read + admin-management.

---

## 4. Technology summary

| Concern | Technology |
|---|---|
| Mobile client | Flutter (Dart) |
| Web client | Next.js 16 · React 19 · TypeScript · Tailwind v4 · TanStack Query · Recharts |
| Backend API | FastAPI (async), Python 3.11+ |
| ORM / migrations | SQLAlchemy 2.0 (async) · Alembic |
| Database | PostgreSQL |
| Auth | JWT (HS256, `python-jose`) · bcrypt (`passlib`) |
| File storage | Local `/uploads` via StaticFiles (S3-pluggable via `storage_service`) |
| PDF reports | `pdf_service` (server-side render) |
| Deployment (planned) | Docker · Nginx · HTTPS/SSL · VPS |
