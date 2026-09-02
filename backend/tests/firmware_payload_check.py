"""Post the exact JSON strings allsensors.ino's postToServer() builds, as raw bytes.

Run like tests/telemetry_check.py (live backend on :8000 + seeded dev DB).

Not a re-test of the schema — a check that the string concatenation in the
sketch produces something the endpoint accepts, including the null branches.
"""
import asyncio

import httpx

BASE = "http://localhost:8000/api/v1"
INC1 = "bbbbbbbb-0002-0002-0002-000000000001"
ADMIN = {"email": "admin@neonatal.rs", "password": "Password123!"}

# Byte-for-byte what the sketch concatenates, for each sensor state.
CASES = [
    ("finger on probe, all sensors healthy",
     '{"heart_rate":138,"spo2":97,"suhu_bayi":36.8,"suhu_inkubator":29.5,"kelembapan_inkubator":55}',
     201),
    ("no finger (HR/SpO2 null), temps fine",
     '{"heart_rate":null,"spo2":null,"suhu_bayi":36.8,"suhu_inkubator":29.5,"kelembapan_inkubator":55}',
     201),
    ("DS18B20 unplugged -> appendNum emits null",
     '{"heart_rate":138,"spo2":97,"suhu_bayi":null,"suhu_inkubator":29.5,"kelembapan_inkubator":55}',
     201),
    ("everything dead -> device alive, nothing stored",
     '{"heart_rate":null,"spo2":null,"suhu_bayi":null,"suhu_inkubator":null,"kelembapan_inkubator":null}',
     202),
]


async def main():
    ok = True
    async with httpx.AsyncClient(timeout=10) as c:
        token = (await c.post(f"{BASE}/auth/login", json=ADMIN)).json()["access_token"]
        h = {"Authorization": f"Bearer {token}"}
        await c.delete(f"{BASE}/incubators/{INC1}/device", headers=h)
        key = (await c.post(f"{BASE}/incubators/{INC1}/device", headers=h, json={})).json()["device_key"]

        hdr = {"X-Device-Key": key, "Content-Type": "application/json"}
        for name, body, want in CASES:
            r = await c.post(f"{BASE}/telemetry", headers=hdr, content=body.encode())
            good = r.status_code == want
            ok &= good
            print(f"  [{'PASS' if good else 'FAIL'}] {name}: {r.status_code} (want {want})")

        # The old prototype payload must now be rejected outright, not silently
        # half-accepted — otherwise an un-reflashed device looks healthy.
        old = ('{"incubator_id":"INC-01","baby_id":"BABY-01","sensors":'
               '{"heart_rate":120,"spo2":97,"ds18b20_temp":36.8,"dht22_temp":29.5,"dht22_humidity":55}}')
        r = await c.post(f"{BASE}/telemetry", headers=hdr, content=old.encode())
        good = r.status_code == 422
        ok &= good
        print(f"  [{'PASS' if good else 'FAIL'}] stale firmware payload rejected: {r.status_code} (want 422)")

    print("\nall good" if ok else "\nFAILURES")
    return 0 if ok else 1


raise SystemExit(asyncio.run(main()))
