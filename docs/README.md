# Technical Documentation — Neonatal Care System

Design & architecture documentation for the **Sistem Monitoring Bayi pada Inkubator**
(Neonatal Care System) — a Flutter (mobile) + Next.js (web) + FastAPI/PostgreSQL platform for
monitoring newborns in NICU/perinatology incubators, with parent-involvement tracking and reporting.

All diagrams use [Mermaid](https://mermaid.js.org/) and render directly on GitHub and in VS Code
(with the *Markdown Preview Mermaid Support* extension). See each diagram file's "How to view" note.

### 🚀 Building the frontend? Start here
| Document | Contents |
|---|---|
| [GETTING_STARTED.md](GETTING_STARTED.md) | **Frontend Integration Guide** — auth flow, a ready-made typed API client, error handling, and common recipes (dashboard, monitoring, photo upload, PDF) |
| [api-types.ts](api-types.ts) | **Copy-paste TypeScript types** for every request & response, including required/optional/nullable markers |
| [API.md](API.md) | **API reference** — per-endpoint request/response detail, field tables, RBAC, error formats, endpoint matrix |

### 🏗️ Design & architecture
| Document | Contents |
|---|---|
| [ERD.md](ERD.md) | **Entity Relationship Diagram** — 10-table PostgreSQL schema, columns, enums, relationships, constraints |
| [COMPONENT_DIAGRAM.md](COMPONENT_DIAGRAM.md) | **Component / Architecture Diagram** — clients, Next.js BFF, FastAPI layered architecture, persistence |
| [SEQUENCE_DIAGRAMS.md](SEQUENCE_DIAGRAMS.md) | **Sequence Diagrams** — login, monitoring + vital evaluation, baby registration, involvement (Pillar 6) scoring, PDF export, admin |

> Documentation is reverse-engineered from and verified against the live backend in `../backend/app/`.
> The running API also exposes interactive docs at `/docs` (Swagger UI) and `/redoc`.

## System at a glance

- **Actors:** Admin (user management, audit), Perawat/Nurse (registration, monitoring, involvement),
  Dokter/Doctor (read-only dashboards & reports).
- **Clinical model:** implements the **IFCDC 8-Pillar** neonatal care framework. Six pillars form the
  **Observation** (Monitoring Bayi) instrument (42 items, 0–3 each); the other two are their own
  6-item modules: Pillar 6 "Kerjasama dengan Keluarga" → **Parent involvement**, Pillar 8 "Kolaborasi
  Interprofesional" → **Menu Aksi**. All roll up to a percentage + 5-band category.
- **Auth:** JWT Bearer for mobile; httpOnly-cookie BFF for web. Every mutation is audit-logged.
