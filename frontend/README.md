# Neonatal Care — Mobile App (Flutter)

The bedside data-entry client for the Neonatal Care System: nurses register babies, record vital-sign monitoring and parent-involvement sessions, upload photos, and view reports — optimised for use at the cot-side.

→ See the [root README](../README.md) for the full-stack overview, and the [backend README](../backend/README.md) for the API.

---

## Tech Stack

| Concern | Choice |
|---|---|
| Framework | Flutter (Dart) |
| State | Riverpod |
| Networking | Dio (with JWT interceptor) |
| Routing | go_router |
| Charts | fl_chart |
| Secure storage | flutter_secure_storage (JWT) |
| Fonts | google_fonts (Manrope) |

---

## Project Structure

```
lib/
├── core/
│   ├── theme/      app_theme.dart  (clean-clinical design tokens)
│   ├── router/     app_router.dart (go_router + auth redirect)
│   ├── api/        api_client.dart (Dio + Bearer interceptor), endpoints
│   ├── providers/  auth provider
│   ├── models/     baby, dashboard, involvement, …
│   └── widgets/    StatCard, StatusBadge, ScoreChips, …
├── features/
│   ├── auth/         login
│   ├── dashboard/    incubator grid + stats
│   ├── baby/         registration (stepper)
│   ├── monitoring/   vitals entry + photo upload
│   ├── involvement/  parent-involvement entry (live score)
│   ├── reports/      report + vital-trend charts + PDF export
│   ├── incubator/    incubator detail
│   └── admin/        user management · audit log
└── main.dart
```

---

## Getting Started

### Prerequisites
- Flutter SDK 3.44+
- A running [backend](../backend/README.md) on `http://localhost:8000`

### Run
```bash
flutter pub get
flutter run -d chrome --web-port 5000    # web
# or: flutter run                         # connected device / emulator
```

The API base URL is configured in `lib/core/api/api_endpoints.dart`
(`baseUrl = http://localhost:8000`).

Log in with a seeded account (e.g. `siti.aisyah@neonatal.rs` / `Password123!`).

---

## Auth

On login the JWT is persisted via `flutter_secure_storage`; a Dio interceptor
attaches it as `Authorization: Bearer <token>` on every request. `go_router`
redirects unauthenticated users to `/login`. PDF export passes the token as a
`?token=` query param since the browser tab can't set headers.

---

## Design

The app uses a clean-clinical theme (Manrope type, `#2563EB` primary, slate ink,
soft card shadows) defined in `lib/core/theme/app_theme.dart` — matched 1:1 by
the Next.js web dashboard so both clients feel like one product.
