# Real-Time IoT Incubator Monitoring — Design

> Feature spec for streaming live sensor telemetry from each incubator into the NeoNatal
> stack: real-time graphs, an alert engine, and an on-demand device simulator.
>
> **Status:** design locked (2026-07-30) · **Phase 0 not started.**
> Source spec: `docs/specs/updates03/Incubator Monitoring System integrated with IoT.png`.

---

## 1. Goal

Automate the numeric vitals that nurses currently type into the monitoring form by feeding
them from per-incubator sensors, add real-time trend graphs, and raise alerts on critical
events — all on a local network, demoed entirely in software (no hardware yet).

The reference diagram shows a "Secure Cloud Server," but the real target is the **hospital
LAN**. Those aren't in conflict: the same containerized stack runs on an on-prem box instead
of the VPS. For the portfolio demo it all runs locally + a device **simulator**.

### Sensor → existing-field mapping
6 of the spec's sensors automate fields already in `monitoring_records`; 4 are net-new.

| Spec sensor | Field | Status |
|---|---|---|
| Temperature (Air) | `suhu_inkubator` | existing (was manual) |
| Temperature (Skin) | `suhu_bayi` | existing (was manual) |
| Humidity | `kelembapan_inkubator` | existing (was manual) |
| SpO₂ | `spo2` | existing (was manual) |
| Heart Rate | `heart_rate` | existing (was manual) |
| Respiratory Rate | `respiratory_rate` | existing (was manual) |
| Noise / Light / Door / Weight | — | **new** (Pillar 7 environment) |

`pain_score`, `sleep_*`, photo, expression/movement stay **manual** (NIPS/observational, not
sensor-derived).

---

## 2. Locked decisions

| Dimension | Decision | Rationale |
|---|---|---|
| Deployment | All-local Docker Compose (simulator-first, software demo) | No hardware; same stack can later run on a ward LAN box or the VPS |
| Transport | **MQTT** (Mosquitto) — sim publishes, backend subscribes via `aiomqtt` | Industry-standard IoT; free offline-detection via Last-Will |
| Storage | New **`sensor_readings`** table + in-memory live buffer | Keep high-frequency telemetry out of the clinical `monitoring_records` table |
| Delivery | **WebSocket** — browser via short-lived ticket, Flutter via Bearer | True push / real-time graph |
| Simulator | Realistic drifting vitals **+ on-demand scenario injection** | Fire alarms live during a demo to showcase the alert engine |

---

## 3. End-to-end architecture

```
simulator (N incubators, ~1 Hz, scenario control)
   │  publish  incubator/{no}/telemetry     (+ retained .../status, LWT)
   ▼
Mosquitto broker ──► FastAPI aiomqtt subscriber (lifespan background task)
                        ├─ validate → INSERT sensor_readings
                        ├─ update in-memory live buffer (last ~2 min per incubator)
                        ├─ alert engine → flip incubators.status='warning' + sensor_alerts
                        └─ fan-out to WebSocket connections (per incubator)
                                   ▼
              web (Recharts, sliding window)   /   Flutter (live chart)
```

New containers in `docker-compose.yml`: **`mosquitto`** and **`simulator`**.

---

## 4. Telemetry contract (MQTT)

**Topics**
- `incubator/{incubator_no}/telemetry` — QoS 1, not retained. The reading stream.
- `incubator/{incubator_no}/status` — retained; MQTT **Last-Will** publishes `{"online": false}`
  when a device drops → offline detection for free.
- `incubator/{incubator_no}/command` — optional; scenario control if routed via MQTT instead of
  the simulator's HTTP control.

**Payload** (keys mirror `monitoring_records` for 1:1 auto-fill — zero mapping layer)
```json
{
  "incubator_no": "INC-01",
  "ts": "2026-07-30T10:15:03Z",
  "suhu_inkubator": 34.2,
  "suhu_bayi": 36.6,
  "kelembapan_inkubator": 62.0,
  "spo2": 97.0,
  "heart_rate": 142,
  "respiratory_rate": 48,
  "noise_db": 52.0,
  "light_lux": 180,
  "door_open": false,
  "weight_g": 1450
}
```

---

## 5. Data model

### `sensor_readings` (new — high-frequency, separate from clinical)
| Column | Type | Notes |
|---|---|---|
| `reading_id` | UUID PK | |
| `incubator_id` | UUID FK → incubators | |
| `baby_id` | UUID FK → babies, nullable | denormalized from the current assignment at ingest |
| `recorded_at` | timestamptz | from payload `ts` |
| `suhu_inkubator` | Numeric(4,1) | air temp °C |
| `suhu_bayi` | Numeric(4,1) | skin temp °C |
| `kelembapan_inkubator` | Numeric(5,2) | % RH |
| `spo2` | Numeric(5,2) | % |
| `heart_rate` | SmallInteger | bpm |
| `respiratory_rate` | SmallInteger | breaths/min |
| `noise_db` | Numeric(5,2) | dB (Pillar 7) |
| `light_lux` | Integer | lux (Pillar 7) |
| `door_open` | Boolean | (Pillar 7) |
| `weight_g` | Integer | integrated scale |
| `source` | Enum(`simulator`,`sensor`) | provenance |
| `created_at` | timestamptz | server default |

Index `(incubator_id, recorded_at DESC)`. Retention/downsampling deferred to P4.

### `sensor_alerts` (new — P3)
`alert_id` PK · `incubator_id` FK · `baby_id` FK (nullable) · `alert_type`
(`desaturation`/`bradycardia`/`tachycardia`/`apnea`/`temp_out_of_range`/`door_open`/`environment`)
· `severity` (`warning`/`critical`) · `value` · `threshold` · `started_at` · `resolved_at`
(nullable) · `acknowledged_by` FK (nullable) · `acknowledged_at` (nullable).

> **Fresh-DB rule:** every migration here must ALSO be reflected in
> `backend/database/schema.sql` — Alembic can't build the DB from scratch (see §9).

---

## 6. Alert engine

Runs inline in the ingest path. On threshold breach → open/refresh a `sensor_alerts` row and
set `incubators.status='warning'`; on recovery → resolve the alert and restore status
(`terisi`). Defaults (configurable later):

| Event | Rule | Severity |
|---|---|---|
| Desaturation | SpO₂ < 90 (crit < 85) | warning / critical |
| Bradycardia / Tachycardia | HR < 100 / HR > 180 | warning |
| Apnea | RR < 10 | critical |
| Temp out of range | air ∉ 34–36 °C · skin ∉ 36.0–37.5 °C | warning |
| Door open too long | `door_open` sustained > 60 s | warning |
| Environment (soft) | noise > 60 dB · light > threshold | info/warning |

Maps directly onto the diagram's 5 alert types and the **existing** `incubator_status` enum —
no new status states needed.

---

## 7. Real-time delivery (WebSocket)

- **Endpoint:** `GET /api/v1/incubators/{id}/stream?ticket=<short-lived-jwt>` (WS upgrade).
- **On connect:** send a backfill of the last window (~2 min) so the graph isn't empty, then
  stream each new reading as it arrives from MQTT.
- **Backfill REST** (also used for reloads): `GET /api/v1/incubators/{id}/readings?limit=120`.
- **Connection manager:** in-process `dict[incubator_id → set[WebSocket]]`; the MQTT subscriber
  calls `broadcast(incubator_id, reading)`.
- **Auth:** browser can't send a Bearer header on a WS handshake, so mint a **short-lived
  ticket** server-side (same spirit as the PDF-export `?token=` flow) via a Next BFF route.
  Flutter passes its Bearer directly.

### ⚠️ BFF caveat (decision, not a surprise)
The web dashboard's cookie→Bearer BFF means a browser WS **punctures** it — the browser must
reach FastAPI directly with the ticket. Fine for the local demo (`localhost:8000`). For the VPS
you'd expose an `api.<domain>` host or proxy WS through Next. Flutter is unaffected.

---

## 8. Device simulator (Phase 0 centerpiece)

- One Python container. Per incubator, maintains vitals state and applies a **bounded
  random-walk** within preterm bands: HR 120–160, RR 40–60, SpO₂ 90–100, skin 36.5–37.5,
  air 34–36, humidity 60–80. Publishes to `incubator/{no}/telemetry` at a configurable rate
  (default ~1 Hz).
- **Scenario control** — `POST /scenario {incubator_no, type, duration_s}` (small HTTP control
  surface on the sim). Types: `desat`, `apnea`, `brady`, `tachy`, `temp_high`, `temp_low`,
  `door_open`. Perturbs the relevant channel for the duration, then recovers — so alarms can be
  fired live during a demo.
- Incubator list sourced from env or a one-time `GET /incubators` at startup, matched to seeded
  `incubator_no`s for continuity with existing data.

---

## 9. Visualization

- **Web — incubator detail:** live Recharts line chart with a **sliding window** (last ~120
  points; ring buffer to avoid re-rendering a growing series), metric toggles / small multiples,
  threshold bands, a connection-status indicator, and WS auto-reconnect.
- **Web — dashboard grid (P4):** per-incubator sparkline + live status dot.
- **Flutter:** live chart on the incubator/monitoring screen via WS.

---

## 10. Integration with existing modules

- **Auto-fill "Input Tanda Vital" (P4):** the latest reading pre-populates the monitoring form
  (temp/HR/SpO₂/RR/humidity); the nurse confirms and adds the manual scores (pain/sleep/photo).
  Turns the all-manual form into "review & attest."
- **Warning status:** the alert engine reuses the existing `incubators.status='warning'` — the
  dashboard already renders it.

---

## 11. Non-goals (this feature)
Parent portal/app · ML risk-scoring engine (thresholds only) · real hardware drivers ·
production TLS for MQTT/WS (LAN-plain for the demo).

---

## 12. Phased plan

| Phase | Scope | Done when |
|---|---|---|
| **P0** | Telemetry contract + Mosquitto in compose + simulator (vitals + scenarios) | Messages visible on the broker (`mosquitto_sub`) |
| **P1** | `aiomqtt` subscriber, `sensor_readings` (migration **+ schema.sql**), live buffer, backfill endpoint | Readings persist + backfill returns data |
| **P2** | WS endpoint + connection manager + ticket auth; web detail live chart; Flutter chart | Graph updates in real time |
| **P3** | Alert engine → `warning` + `sensor_alerts` feed + acknowledge; wire sim scenarios to each alert | Firing a scenario raises + clears an alarm |
| **P4** | Dashboard sparklines/status, auto-fill vitals form, retention/downsampling, LWT offline badges | Polish complete |

---

## 13. Implementation landmines / repo conventions

- **Dual git repos:** backend changes → outer `main` **and** nested `backend-version2` via an
  isolated worktree (never switch the shared `backend/` tree's branch).
- **schema.sql is source of truth** for fresh DBs — mirror every new migration into
  `backend/database/schema.sql` (+ seed if needed); don't rely on `alembic upgrade` from empty.
- **New deps:** pin `aiomqtt` in `requirements.txt`; verify it resolves to linux/cp313 wheels
  (the container build is strict).
- **Line endings:** pin `mosquitto.conf` (and any `*.conf`/`*.sh`) to **LF** in `.gitattributes`
  — `core.autocrlf=true` would otherwise ship CRLF into the container.
- **Web/Flutter** changes → outer `main` only.

---

## 14. Open / deferred
- Storage retention & downsampling strategy (raw vs 1-min aggregates) — decide in P4.
- Whether scenario control is HTTP-on-sim or an MQTT `command` topic — decide in P0.
- Production WS auth posture (api host vs Next WS proxy) — only if this goes beyond the local demo.
