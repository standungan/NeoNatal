# IoT Telemetry — Implementation Plan

> How one ESP8266 device per incubator streams live vitals into the NeoNatal stack,
> and how that data gets plotted on the incubator detail page (web + Flutter).
>
> **Amends `docs/specs/updates03/DESIGN.md`** (design locked 2026-07-30, Phase 0 never started).
> That spec was written *simulator-first, no hardware*. Working firmware now exists in
> `hardware/`, which invalidates two of its locked decisions — see §1.
>
> **Status:** plan · **Written:** 2026-08-24 · **Supersedes:** DESIGN.md §2 (Transport,
> Delivery), §4 (MQTT contract), §8 (simulator as Phase-0 centerpiece)

---

## 0. Inputs

| Input | What it gives us |
|---|---|
| `hardware/allsensors/allsensors.ino` | Working ESP8266 firmware: MAX30102 (HR/SpO₂), DS18B20 (skin temp), DHT22 (air temp + RH), HTTP POST every 3 s with backoff |
| `hardware/backend/` | Reference ingest + fan-out (Express/Socket.IO/JSONB) — the shape to port, not the code |
| `docs/specs/updates03/DESIGN.md` | Sensor→field mapping, `sensor_readings`/`sensor_alerts` model, alert rules, phasing |
| `backend/app/schemas/incubator.py` `THRESHOLD_METRICS` | Neonatal bounds + per-incubator overrides, **already shipped** with GET/PUT endpoints |

**Goal:** the incubator detail page shows a live, auto-updating chart of that incubator's
vitals, sourced from its own physical device, with threshold bands drawn from the
per-incubator settings that already exist.

---

## 1. Amendments to DESIGN.md

| Dimension | DESIGN.md (locked 2026-07-30) | This plan | Why it changed |
|---|---|---|---|
| **Transport** | MQTT — Mosquitto container + `aiomqtt` subscriber | **HTTP POST → FastAPI** | The firmware already does HTTP well (500 ms timeout cap, exponential backoff to 30 s, non-blocking). MQTT would mean a new container, LWT config, rewriting working firmware, and a new pinned dep — DESIGN.md §13 flags cp313-wheel risk on the strict container build. **This plan adds zero new Python dependencies.** Offline detection (MQTT's real win) is replaced by `devices.last_seen_at` + a staleness check. |
| **Delivery** | WebSocket + short-lived JWT ticket, browser bypasses the BFF | **SSE (`text/event-stream`)** | Telemetry is one-way. SSE rides the *existing* cookie→Bearer BFF (one small change, §5.2), reconnects natively, and deletes the entire ticket-auth workstream plus the "BFF puncture" caveat in DESIGN.md §7. Flutter consumes it via `dio` `ResponseType.stream`. |
| **Data source** | Simulator container (Phase-0 centerpiece) | **Real device**; simulator deferred | Hardware exists. A simulator is still useful for demos without the rig — moved to §13. |
| **Identity in payload** | `incubator_no` string in the JSON body | **`X-Device-Key` header → device → incubator** | The prototype's unauthenticated `POST /api/sensors` lets anything on the LAN inject vitals into a clinical record. The device should authenticate, not merely assert. |
| **`baby_id`** | (not in payload; denormalized at ingest) | **Same — and firmware must stop sending it** | Prototype firmware hardcodes `BABY_ID "BABY-01"` (`allsensors.ino:133`). Baby↔incubator is a runtime assignment that flips on admission/discharge. DESIGN.md §5 already got this right; it is called out here because the firmware violates it today. |
| **Timestamps** | `ts` from the device payload | **Server-assigned `recorded_at`** | ESP8266 has no RTC and the firmware runs no NTP — a device `ts` would be garbage. Server time is authoritative. NTP on the device is optional future work. |
| **Sensor set** | 10 channels (incl. noise/light/door/weight) | **5 real channels**; `respiratory_rate` stays manual; Pillar-7 environment columns deferred until hardware exists | Build for the sensors that exist. Nullable columns with no producer are dead schema. |

**Unchanged and still correct:** separate `sensor_readings` table (not `monitoring_records`),
`sensor_alerts` + alert engine reusing the existing `incubators.status='warning'`, chart on
incubator detail, auto-fill of the vitals form as a later payoff.

---

## 2. Telemetry contract

### 2.1 Endpoint

```
POST /api/v1/telemetry
X-Device-Key: <opaque, >=32 chars>
Content-Type: application/json
```

No JWT. Device auth only. This is the single ingest surface.

### 2.2 Payload

The firmware sends **clinical field names** so there is no mapping layer anywhere
(DESIGN.md §4's reasoning, kept):

```json
{
  "suhu_bayi": 36.8,
  "suhu_inkubator": 29.5,
  "kelembapan_inkubator": 55,
  "heart_rate": 120,
  "spo2": 97
}
```

Sensor → field, for the record:

| Device sensor | Firmware key today | Payload field | Column |
|---|---|---|---|
| DS18B20 probe | `ds18b20_temp` | `suhu_bayi` | `sensor_readings.suhu_bayi` |
| DHT22 temp | `dht22_temp` | `suhu_inkubator` | `sensor_readings.suhu_inkubator` |
| DHT22 humidity | `dht22_humidity` | `kelembapan_inkubator` | `sensor_readings.kelembapan_inkubator` |
| MAX30102 | `heart_rate` | `heart_rate` | `sensor_readings.heart_rate` |
| MAX30102 | `spo2` | `spo2` | `sensor_readings.spo2` |
| — none — | — | — | `respiratory_rate` (manual, always NULL from devices) |

Every field is optional and nullable. Unknown fields are rejected (`extra="forbid"`) — the
prototype's `passthrough()` was right for a hobby JSONB table and wrong for a clinical one.

### 2.3 Null semantics — the critical rule

The firmware emits **`heart_rate: 0` / `spo2: 0` when nothing is on the probe.** Persisting
0 bpm as a real reading is unacceptable here: it would render as a cliff on the chart and
fire a bradycardia alert every time the sensor is off the baby.

- **Firmware fix (primary):** send `null` instead of `0` — see §9.
- **Backend fix (defensive, keep both):** in the normalizer, `heart_rate == 0 → None`,
  `spo2 == 0 → None`. Never trust the device to have been reflashed.
- NaN sensors already serialize to `null` via `appendNum()` — no change needed.
- **All-null reading:** update `devices.last_seen_at`, return `202`, and **skip the INSERT**.
  Keeps device liveness honest without filling the table with empty rows.

### 2.4 Responses

| Code | Meaning |
|---|---|
| `201` | Stored |
| `202` | Accepted, nothing stored (all metrics null) |
| `401` | Unknown or inactive device key |
| `409` | Device exists but is not bound to an incubator |
| `422` | Malformed body / value outside physiological range |

The firmware only logs the code; keep bodies tiny.

### 2.5 Rate and storage volume

Default `POST_INTERVAL_MS = 3000`. That is **28,800 rows/day/incubator** (~8.6 M/month
across 10 incubators). Fine for the demo, real for a ward. Options, decide before P4:

- bump the interval to 5–10 s (vitals do not move meaningfully faster at this fidelity), or
- keep 3 s and add the retention job in P4 (drop raw > 7 days, keep 1-minute aggregates).

Recommendation: keep 3 s for now — it makes the live chart feel genuinely live — and treat
retention as a hard P4 deliverable rather than an "open question."

---

## 3. Data model

### 3.1 `devices` (new)

| Column | Type | Notes |
|---|---|---|
| `device_id` | UUID PK | |
| `incubator_id` | UUID FK → incubators, **UNIQUE**, nullable | UNIQUE is what enforces *one device per incubator* at the DB level |
| `device_key_hash` | TEXT UNIQUE NOT NULL | SHA-256 hex of the key; plaintext shown **once** at creation and never stored |
| `label` | VARCHAR(100) | e.g. "ESP8266 – INC-01" |
| `firmware_version` | VARCHAR(20) nullable | optional, reported later |
| `last_seen_at` | TIMESTAMPTZ nullable | drives the online/offline badge |
| `is_active` | BOOLEAN NOT NULL DEFAULT true | revoke without deleting history |
| `created_at` / `updated_at` | TIMESTAMPTZ | `updated_at` gets the standard `set_updated_at()` trigger |

Lookup is `sha256(header) → indexed equality on device_key_hash`. One query, no scan.

### 3.2 `sensor_readings` (new)

| Column | Type | Notes |
|---|---|---|
| `reading_id` | UUID PK | |
| `incubator_id` | UUID FK → incubators NOT NULL | |
| `baby_id` | UUID FK → babies, nullable | resolved from the **active** assignment at ingest |
| `device_id` | UUID FK → devices, nullable | provenance; nullable so simulator rows are legal |
| `recorded_at` | TIMESTAMPTZ NOT NULL DEFAULT NOW() | server-assigned (§1) |
| `suhu_bayi` | Numeric(4,1) | °C |
| `suhu_inkubator` | Numeric(4,1) | °C |
| `kelembapan_inkubator` | Numeric(5,2) | % RH |
| `heart_rate` | SmallInteger | bpm |
| `spo2` | Numeric(5,2) | % |
| `respiratory_rate` | SmallInteger | no sensor yet; column present for parity |
| `source` | Enum(`sensor`,`simulator`) NOT NULL DEFAULT `sensor` | |
| `created_at` | TIMESTAMPTZ NOT NULL DEFAULT NOW() | |

`CREATE INDEX idx_sensor_readings_incubator_time ON sensor_readings (incubator_id, recorded_at DESC);`

Column types deliberately mirror `monitoring_records` exactly, so the P4 vitals auto-fill is
a straight field copy with no casting.

### 3.3 `sensor_alerts` (P4)

As specified in DESIGN.md §5 — no changes. Restrict `alert_type` to types a real sensor can
raise: `desaturation`, `bradycardia`, `tachycardia`, `temp_out_of_range`. `apnea`,
`door_open`, and `environment` need hardware that does not exist yet.

### 3.4 Migration

- New revision `backend/alembic/versions/<rev>_iot_telemetry.py`,
  **`down_revision = "c9e7b2a4f610"`** (current head — verified: nothing revises it).
- Creates enum `sensor_source`, tables `devices` + `sensor_readings`, the index, and the
  `trg_devices_updated_at` trigger.
- **Mirror every statement into `backend/database/schema.sql`.** Non-negotiable: the db
  container loads `schema.sql` on first boot and the backend then runs `alembic stamp head`
  (see the `command:` block in `docker-compose.yml`). A migration that is not mirrored simply
  does not exist on a fresh database.
- Register both models in `backend/app/models/__init__.py` (imports **and** `__all__`).

---

## 4. Backend

### 4.1 New files

```
app/models/device.py                            Device
app/models/sensor_reading.py                    SensorReading
app/schemas/telemetry.py                        TelemetryIn, SensorReadingResponse, DeviceCreate/Response
app/repositories/device_repository.py           get_by_key_hash, get_by_incubator, touch_last_seen
app/repositories/sensor_reading_repository.py   create, get_recent(incubator_id, limit)
app/services/telemetry_service.py               ingest(), get_recent(), live buffer, SSE broadcast
app/api/v1/telemetry.py                         POST /telemetry
```

### 4.2 Changed files

- `app/api/deps.py` — add `get_current_device` (reads `X-Device-Key`, hashes, looks up,
  401 on miss/inactive). Sits alongside the existing `require_roles` guards.
- `app/api/v1/incubators.py` — add `GET /{id}/readings` (backfill) and `GET /{id}/stream` (SSE).
  Also admin device CRUD: `POST /{id}/device` (returns the plaintext key **once**),
  `DELETE /{id}/device`.
- `app/main.py` — `include_router(telemetry.router, prefix="/api/v1", tags=["Telemetry"])`.
- `app/models/__init__.py` — register the two new models.

### 4.3 Ingest flow — `telemetry_service.ingest(payload, device)`

1. Device already resolved by the dependency (401 handled there).
2. `device.incubator_id` — if NULL → `409`.
3. **Normalize:** `heart_rate == 0 → None`; `spo2 == 0 → None`. Pydantic enforces
   physiological ranges (HR 0–300, SpO₂ 0–100, temps −40–125, RH 0–100) — the same bounds
   the prototype's Zod schema uses.
4. If every metric is `None` → touch `last_seen_at`, return `202`, no INSERT.
5. Resolve `baby_id` from the **active** assignment
   (`BabyIncubatorAssignment.status == "active"` for this incubator; `None` if empty).
6. INSERT `sensor_readings`.
7. `devices.last_seen_at = now()`.
8. Append to the in-memory ring buffer for this incubator (`deque(maxlen=120)` ≈ 6 min @ 3 s).
9. Broadcast to that incubator's SSE subscribers.
10. *(P4)* run the alert engine.

Steps 8–9 are pure in-process state; steps 1–7 are the transactional part.

### 4.4 New endpoints

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `POST` | `/api/v1/telemetry` | `X-Device-Key` | Ingest |
| `GET` | `/api/v1/incubators/{id}/readings?limit=120` | `AnyRole` | Backfill — chart on load/reload, and the P1 polling source |
| `GET` | `/api/v1/incubators/{id}/stream` | `AnyRole` | SSE live stream |
| `POST` | `/api/v1/incubators/{id}/device` | `AdminOnly` | Provision device, returns plaintext key once |
| `DELETE` | `/api/v1/incubators/{id}/device` | `AdminOnly` | Revoke |

Device provisioning writes to `audit_logs` like every other admin mutation in this codebase.

---

## 5. Live delivery (SSE)

### 5.1 Server

- `GET /api/v1/incubators/{id}/stream` returns `text/event-stream` via
  `StreamingResponse` (stdlib + FastAPI, no new dep).
- **On connect:** replay the ring buffer so the chart is never empty, then stream new readings.
- **Keepalive:** a `: ping` comment every 15 s so idle proxies do not drop the connection.
- **Connection manager:** module-level `dict[UUID, set[asyncio.Queue]]`; `ingest()` calls
  `broadcast(incubator_id, reading)`; the generator drains its own queue and always removes
  itself in a `finally`.

> ⚠️ **Single-process assumption.** `docker-compose.yml` runs
> `uvicorn app.main:app --host 0.0.0.0 --port 8000` with **no `--workers`**, so in-process
> fan-out is correct today. If workers are ever added, a POST landing on worker 1 will not
> reach subscribers on worker 2 — that would need Postgres `LISTEN/NOTIFY` or Redis pub/sub.
> Put this in a comment above the connection manager so it is not discovered the hard way.

### 5.2 BFF change (required, ~10 lines)

`web/app/api/v1/[...path]/route.ts` currently does `await upstream.arrayBuffer()` — it fully
buffers every response, which would make SSE hang forever. Change:

- if the upstream `content-type` is `text/event-stream`, return
  `new NextResponse(upstream.body, { status, headers })` — pass the `ReadableStream` straight
  through instead of buffering;
- set `Cache-Control: no-cache`, `Connection: keep-alive`, `X-Accel-Buffering: no`;
- add `export const dynamic = "force-dynamic"` to the route.

Everything else — the cookie→Bearer injection, same-origin, no CORS — stays exactly as is.
**This is the whole reason SSE beats WebSocket here:** the WS path in DESIGN.md §7 required
minting short-lived tickets and having the browser bypass the BFF entirely.

---

## 6. Web — chart on the incubator detail page

Target: `web/app/(app)/incubator/[id]/page.tsx` (Next 16, React 19, TanStack Query,
`recharts@3.8` already installed).

**New files**
- `web/lib/types.ts` — add `SensorReading`.
- `web/hooks/use-sensor-stream.ts` — backfill via `useQuery` + live via `EventSource`;
  auto-falls back to `refetchInterval: 3000` if the stream errors.
- `web/components/sensor-chart.tsx` — the card.

**Chart spec**
- Recharts `LineChart`, sliding window of the last 120 points (fixed-length array, not a
  growing series).
- Metric toggles: HR, SpO₂, skin temp, air temp, humidity. Dual axes (bpm/% left, °C right)
  — the prototype's `VitalsChart`/`EnvChart` split is a reasonable alternative if one chart
  gets crowded.
- **Threshold bands** from `GET /incubators/{id}/thresholds` — that endpoint already ships,
  so the bands are free and automatically respect admin overrides. Use `ReferenceArea`.
- Connection dot: green when a reading arrived < 12 s ago, red otherwise (same staleness
  heuristic as the prototype's `OFFLINE_MS`), plus a "device belum terpasang" empty state
  when the incubator has no device row.
- Gaps, not zeros: a `null` metric must break the line — do **not** pass `connectNulls`.
  (The prototype uses `connectNulls` because it pre-filters zeros client-side; here NULL is
  meaningful — the probe was off the baby.)

**P1 shortcut:** ship the chart on `refetchInterval: 3000` against the backfill endpoint
before SSE exists. At a 3 s device cadence this is visually indistinguishable from streaming,
and it puts the chart on screen a whole phase earlier with zero streaming infrastructure.
Swapping in `EventSource` afterwards touches one hook.

---

## 7. Flutter — chart on the incubator detail screen

Target: `frontend/lib/features/incubator/screens/incubator_detail_screen.dart`
(`fl_chart@0.69` already a dependency; Riverpod + Dio).

- `core/api/api_endpoints.dart` — add
  `incubatorReadings(id)` → `/api/v1/incubators/$id/readings` and
  `incubatorStream(id)` → `/api/v1/incubators/$id/stream`.
- `features/incubator/providers/sensor_readings_provider.dart` — Riverpod provider,
  following `features/dashboard/providers/dashboard_provider.dart`.
- New `_SensorChartCard` widget in the detail screen, slotted between `_IncubatorInfoCard`
  and `_BabyInfoCard`.
- P1: `Timer.periodic(3s)` refetch. P3: swap to SSE via `dio` `ResponseType.stream` plus a
  line splitter parsing `data:` frames. The existing `ApiClient` interceptor already attaches
  the Bearer token, so Flutter needs no auth work at all.

---

## 8. Alert engine (P4)

Rules from DESIGN.md §6, with three corrections:

1. **Thresholds come from `incubator_service.get_thresholds(incubator_id)`**, not hardcoded
   constants — the per-incubator override feature already exists and should be the single
   source of truth for both the alert engine and the chart's threshold bands.
2. **Debounce: N consecutive breaching readings (default 3 ≈ 9 s) before opening an alert.**
   Essential with this hardware — the pulse-ox drops in and out constantly, and a
   single-sample trigger would produce an alarm storm. Symmetrically, require N consecutive
   in-range readings to resolve.
3. **Only metrics with a real sensor can fire.** No apnea (`respiratory_rate` has no
   producer), no door/noise/light.

On breach: upsert an open `sensor_alerts` row and set `incubators.status = 'warning'`.
On recovery: resolve the row and restore status — to `'terisi'` **only if an active
assignment exists**, otherwise `'kosong'`. (Naively restoring `'terisi'` would mark an empty
incubator as occupied.)

---

## 9. Firmware changes

File: `hardware/allsensors/allsensors.ino`. Everything else in the sketch — sampling,
the RF algorithm, median filtering, OLED, the 500 ms timeout cap and backoff — is untouched.

1. **Delete `BABY_ID`** (`:133`) and stop sending it. The server resolves the baby.
2. **Replace `INCUBATOR_ID` with `DEVICE_KEY`**, sent as the `X-Device-Key` header.
3. `SERVER_URL` → `http://<host>:8000/api/v1/telemetry`.
4. **Rename JSON keys** to the clinical names in §2.2.
5. **Send `null`, not `0`,** when `displayBpm == 0` / `displaySpo2 == 0`.
6. **Move WiFi credentials out of the tracked source** — see §11.

Resulting body of `postToServer()`:

```cpp
String json = "{";
if (displayBpm > 0)  { json += "\"heart_rate\":"; json += displayBpm; json += ','; }
else                   json += "\"heart_rate\":null,";
if (displaySpo2 > 0) { json += "\"spo2\":"; json += (int)(displaySpo2 + 0.5f); json += ','; }
else                   json += "\"spo2\":null,";
appendNum(json, "suhu_bayi",            probeTempC,   1); json += ',';
appendNum(json, "suhu_inkubator",       roomTempC,    1); json += ',';
appendNum(json, "kelembapan_inkubator", roomHumidity, 0);
json += "}";
...
http.addHeader("X-Device-Key", DEVICE_KEY);
```

---

## 10. Phases

| Phase | Scope | Done when |
|---|---|---|
| **P0 — Ingest + storage** | `devices` + `sensor_readings` (migration **+ schema.sql**), models/schemas/repos, `get_current_device`, `POST /telemetry`, admin device provisioning, firmware §9 | `curl` with a valid device key inserts a row with the right `baby_id`; a key-less POST gets 401; the ESP's serial shows `[POST] 201`; HR/SpO₂ land as NULL with no finger on the probe |
| **P1 — Backfill + web chart (polling)** | `GET /{id}/readings`, `SensorReading` type, `use-sensor-stream` hook on `refetchInterval`, `sensor-chart.tsx` wired into the detail page with threshold bands | The incubator page draws a live chart from the real device, bands and offline badge working |
| **P2 — Push** | SSE endpoint + connection manager + ring buffer; BFF streaming passthrough (§5.2); hook swaps `EventSource` in with polling as fallback | Chart updates with no polling; killing the device flips the badge to offline within 12 s |
| **P3 — Flutter** | Endpoints, provider, `_SensorChartCard`, then SSE via dio | Same chart live on the Flutter incubator detail screen |
| **P4 — Alerts + payoff** | Alert engine with debounce → `warning` + `sensor_alerts` + acknowledge; retention/downsampling; vitals-form auto-fill; dashboard sparklines | Pulling the probe raises and then clears a real alert; the monitoring form pre-fills from the latest reading |

P0+P1 is the smallest slice that satisfies the actual request ("stream per device, plot on
the incubator page"). P2–P4 are refinement.

---

## 11. Landmines

- **Committed WiFi credentials.** `allsensors.ino:130-131` contains a real SSID and password
  in plaintext, and `hardware/` is currently **untracked** — this gets committed the
  moment someone runs `git add`. Move them to an untracked `secrets.h` (with a
  `secrets.example.h` committed) *before* the first commit of that folder. Same treatment for
  `DEVICE_KEY`.
- **`hardware/backend/dist` and `hardware/frontend/dist`** are build output not
  covered by `.gitignore` (`node_modules` and `.env` are). Add them.
- **`schema.sql` is the real source of truth** for fresh databases — mirror every migration.
  Alembic cannot build this DB from empty; `docker-compose.yml` documents why.
- **Dual git repos** (DESIGN.md §13): backend changes go to the outer `main` **and** the
  nested `backend-version2` via an isolated worktree — never switch the shared `backend/`
  tree's branch. Web/Flutter changes go to the outer `main` only.
- **Single-worker uvicorn** — see §5.1.
- **BFF buffering** — see §5.2; SSE silently hangs if this is missed.
- **Row volume** — see §2.5.
- **Clinical caveat, non-blocking:** a transmissive fingertip pulse-ox will not read reliably
  on a neonate as currently mounted, and `SPO2_CAL_B` is still the literature slope
  (uncalibrated). Data quality is a probe/hardware conversation; it does not block any of the
  software above, but the demo should not be presented as clinically accurate.

---

## 12. Verification

`backend/tests/` is empty — there is no automated suite to hook into, so verification is
explicit:

- **Ingest:** add a `Telemetry` folder to `NeoNatal.postman_collection.json` (valid POST,
  bad key → 401, unbound device → 409, all-null → 202, out-of-range → 422).
- **Normalizer self-check:** a small assert script covering the 0→NULL rule and the range
  bounds — mirrors the convention the prototype already uses in
  `hardware/backend/src/validation.test.ts` (plain asserts, no framework).
- **End-to-end:** device powered on → row count climbs → chart animates → pull the probe →
  HR/SpO₂ lines break (not drop to zero) → power off the device → offline badge within 12 s.
- **Web:** verify the chart in the browser preview (console clean, network shows the stream
  staying open, screenshot the live chart).

---

## 13. Deferred / open

- **Device simulator** — no longer Phase 0, but still worth a small script that POSTs to
  `/api/v1/telemetry` with a bounded random walk, for demos without the rig. Cheap now that
  ingest is plain HTTP.
- **Retention & downsampling** — decide before P4 (§2.5).
- **NTP on the device** — would allow trusting a device `ts` and detecting clock skew.
- **MQTT** — revisit if the deployment grows to many devices at ≥1 Hz, or needs
  server→device commands. The ingest service boundary is drawn so that swapping transport
  means adding a subscriber that calls the same `ingest()`.
- **Multi-worker fan-out** (Postgres `LISTEN/NOTIFY`) — only if uvicorn gains `--workers`.
- **Pillar-7 environment sensors** (noise/light/door/weight) — schema additions when hardware
  exists.
