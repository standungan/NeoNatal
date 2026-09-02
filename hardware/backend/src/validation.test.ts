// Self-check skema validasi (jalankan: npm run check). Tanpa framework, cuma assert.
import assert from "node:assert";
import { readingSchema } from "./validation.js";

// Payload valid dari ESP8266 (semua sensor terisi)
assert.ok(
  readingSchema.safeParse({
    incubator_id: "INC-01",
    baby_id: "BABY-01",
    sensors: { heart_rate: 120, spo2: 97, ds18b20_temp: 36.8, dht22_temp: 29.5, dht22_humidity: 55 },
  }).success
);

// No-finger: HR/SpO2 = 0, env null -> tetap valid
assert.ok(
  readingSchema.safeParse({
    incubator_id: "INC-01",
    baby_id: "BABY-01",
    sensors: { heart_rate: 0, spo2: 0, ds18b20_temp: null, dht22_temp: null, dht22_humidity: null },
  }).success
);

// Sensor baru (belum ada di skema) harus lolos berkat passthrough()
assert.ok(
  readingSchema.safeParse({
    incubator_id: "INC-01",
    baby_id: "BABY-01",
    sensors: { heart_rate: 90, co2_ppm: 400 },
  }).success
);

// incubator_id kosong -> ditolak
assert.equal(readingSchema.safeParse({ incubator_id: "", baby_id: "B", sensors: {} }).success, false);

// SpO2 di luar 0..100 -> ditolak
assert.equal(
  readingSchema.safeParse({ incubator_id: "I", baby_id: "B", sensors: { spo2: 150 } }).success,
  false
);

console.log("validation.test.ts OK");
