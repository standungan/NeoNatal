# Baby Monitor — Dashboard IoT (ESP8266 + MAX30102 + DS18B20 + DHT22)

> ### ⚠️ Firmware sekarang mengirim ke backend NeoNatal, bukan ke folder ini
>
> Sejak P0 (`docs/specs/updates03/IMPLEMENTATION_PLAN.md`), `allsensors/` mem-POST ke
> **FastAPI** di `POST /api/v1/telemetry` (`:8000`) dengan header `X-Device-Key`,
> memakai nama field klinis (`suhu_bayi`, `suhu_inkubator`, `kelembapan_inkubator`).
> Identitas alat = device key; inkubator & bayi ditentukan server.
>
> Stack **Express + React di folder ini adalah prototipe standalone yang asli** —
> disimpan sebagai referensi & sebagai alat bring-up hardware (kalau mau menguji
> rig tanpa menyentuh sistem utama, checkout firmware versi lama). Bagian 1–3 di
> bawah menjelaskan prototipe itu; bagian 4 (firmware) & wiring tetap berlaku.

Monitoring inkubator bayi realtime: heart rate & SpO2 (MAX30102), suhu probe
(DS18B20), suhu & kelembaban ruang (DHT22).

> Alat edukasi/hobi — **bukan alat medis**, tidak untuk diagnosis.

```
# sekarang (produksi)
ESP8266 ──HTTP POST /api/v1/telemetry──▶ FastAPI (NeoNatal) ──▶ PostgreSQL: sensor_readings

# prototipe asli (folder ini, referensi)
ESP8266 ──HTTP POST──▶ backend (Express + Socket.IO + PostgreSQL) ──WebSocket──▶ dashboard (React)
```

## Struktur

```
backend/     Express + TS, REST + Socket.IO, PostgreSQL (JSONB)
frontend/    React + TS (Vite) + Tailwind + Recharts
allsensors/  Firmware ESP8266 (sketch Arduino) — sudah + WiFi/HTTP POST
```

## 1. Database (PostgreSQL)

Install & buat DB + user (Ubuntu/Debian):

```bash
sudo apt update && sudo apt install -y postgresql
sudo -u postgres psql -c "CREATE USER baby WITH PASSWORD 'baby';"
sudo -u postgres psql -c "CREATE DATABASE babymon OWNER baby;"
```

Tabel `readings` dibuat otomatis saat backend pertama kali jalan (tidak perlu
migration manual).

## 2. Backend

```bash
cd backend
cp .env.example .env      # sesuaikan DATABASE_URL kalau perlu
npm install
npm run dev               # http://localhost:4000
```

Cek: `curl localhost:4000/api/health` → `{"ok":true}`.
Self-check validasi: `npm run check`.

Endpoint:
- `POST /api/sensors` — terima `{ incubator_id, baby_id, sensors:{...} }`, simpan + broadcast.
- `GET /api/sensors/latest?incubator_id=INC-01` — reading terakhir (load awal dashboard).

## 3. Frontend

```bash
cd frontend
npm install
npm run dev                # http://localhost:5173
```

Saat dev, Vite mem-proxy `/api` & `/socket.io` ke backend `:4000`, jadi tak perlu
set `VITE_BACKEND_URL`. Ganti `incubator_id` yang dimonitor lewat kotak input di
kanan atas.

## Serve backend + frontend jadi SATU port (produksi / akses dari HP)

Backend otomatis nyajikan dashboard hasil build dari `frontend/dist` — jadi
API, WebSocket, dan dashboard semua di **satu URL `:4000`** (tanpa CORS, ESP &
dashboard tinggal pakai IP yang sama).

```bash
# 1) build frontend jadi file statis
cd frontend && npm run build          # menghasilkan frontend/dist

# 2) jalankan backend (nyajikan API + dashboard sekaligus)
cd ../backend && npm run dev          # atau: npm run build && npm start
```

Buka **`http://<IP-LAN-KOMPUTER>:4000`** (mis. dari HP di WiFi yang sama).
`SERVER_URL` di firmware & URL dashboard sekarang sama-sama `:4000`.

> Dua mode: **dev** = dua server (`:5173` + `:4000`, hot-reload) · **satu port**
> = build dulu lalu backend saja (`:4000`). Cukup rebuild frontend tiap ada
> perubahan UI.

## 4. Firmware ESP8266 (`allsensors/`)

Library (sudah terpasang di mesin ini): SparkFun MAX3010x, Adafruit SSD1306 +
GFX, DHT sensor library, OneWire, DallasTemperature.

Konfigurasi tidak lagi di dalam `.ino` — semuanya di `secrets.h` yang
**gitignored**. Salin templatnya dulu:

```bash
cp allsensors/secrets.example.h allsensors/secrets.h
```

```cpp
#define WIFI_SSID      "NAMA_WIFI"
#define WIFI_PASSWORD  "PASSWORD_WIFI"
#define SERVER_URL     "http://<IP-LAN-KOMPUTER>:8000/api/v1/telemetry"
#define DEVICE_KEY     "<hasil provisioning>"
```

`<IP-LAN-KOMPUTER>` = IP komputer yang menjalankan backend (ESP & komputer harus
di WiFi 2.4GHz yang sama). Cek dengan `ipconfig` / `hostname -I`.

**Device key** dibuat sekali oleh admin:

```bash
curl -X POST http://<IP>:8000/api/v1/incubators/<incubator_id>/device \
  -H "Authorization: Bearer <token-admin>" -H "Content-Type: application/json" -d '{}'
```

Field `device_key` di respons **hanya muncul sekali** (server cuma menyimpan
SHA-256-nya) — tempel ke `secrets.h`. Key inilah identitas alat: backend
memetakan key → device → inkubator → bayi (dari penempatan yang sedang aktif).
Karena itu firmware tidak lagi mengirim `incubator_id` maupun `baby_id`.

Upload lewat Arduino IDE (board: *NodeMCU 1.0 (ESP-12E)*, port `/dev/ttyUSB0`),
lalu buka Serial Monitor 115200 baud. Payload yang dikirim tiap 3 detik:

```json
{ "heart_rate":120, "spo2":97, "suhu_bayi":36.8,
  "suhu_inkubator":29.5, "kelembapan_inkubator":55 }
```

Nama field = nama field klinis di database, jadi tak ada lapisan pemetaan di
server. `heart_rate`/`spo2` dikirim **`null`** (bukan 0) saat tidak ada jari, dan
nilai suhu `null` saat sensor error — `null` berarti "tidak ada bacaan", bukan
nol. Tidak ada timestamp: server yang menstempel waktu (ESP8266 tanpa RTC).

Kode respons: `201` tersimpan · `202` alat hidup tapi semua sensor kosong ·
`401` device key salah · `409` device belum terpasang ke inkubator · `422`
payload tidak valid. Selain 2xx, firmware mundur (backoff) sampai 30 detik.

## Wiring ESP8266

| Sensor | Pin |
|---|---|
| MAX30102 / OLED (I2C) | SDA=D2 (GPIO4), SCL=D1 (GPIO5), VIN=3V3 |
| DHT22 data | D5 (GPIO14) |
| DS18B20 data | D6 (GPIO12) + pull-up 4.7k ke 3V3 |
| Button (ganti halaman OLED) | D7 (GPIO13) → GND |
