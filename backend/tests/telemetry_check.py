"""P0 acceptance run: exercises every branch of POST /api/v1/telemetry.

Plain asserts, no framework — same spirit as the prototype's
incubator_iot/backend/src/validation.test.ts.

Needs a LIVE backend on :8000 and the seeded dev database (it logs in as the
seeded admin and provisions throwaway devices on INC-01 / INC-03):

    python -m uvicorn app.main:app --port 8000     # in one shell
    python tests/telemetry_check.py                # in another

Exits non-zero on any failure.
"""
import asyncio
import os

import asyncpg
import httpx
from dotenv import load_dotenv

load_dotenv(".env")
DB = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
BASE = "http://localhost:8000/api/v1"
INC1 = "bbbbbbbb-0002-0002-0002-000000000001"  # terisi — Ahmad Rizki
INC3 = "bbbbbbbb-0002-0002-0002-000000000003"  # kosong

ADMIN = {"email": "admin@neonatal.rs", "password": "Password123!"}
KEY1 = KEY3 = None

results = []


def check(name, got, want):
    ok = got == want
    results.append(ok)
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: got {got!r}, want {want!r}")


async def provision(c, token, incubator_id):
    """Fresh device for this run — revoke any existing binding first."""
    h = {"Authorization": f"Bearer {token}"}
    await c.delete(f"{BASE}/incubators/{incubator_id}/device", headers=h)
    r = await c.post(f"{BASE}/incubators/{incubator_id}/device", headers=h, json={})
    r.raise_for_status()
    return r.json()["device_key"]


async def main():
    global KEY1, KEY3
    async with httpx.AsyncClient(timeout=10) as c:
        token = (await c.post(f"{BASE}/auth/login", json=ADMIN)).json()["access_token"]
        KEY1 = await provision(c, token, INC1)
        KEY3 = await provision(c, token, INC3)

        h1 = {"X-Device-Key": KEY1}
        h3 = {"X-Device-Key": KEY3}

        print("\n1. Auth")
        r = await c.post(f"{BASE}/telemetry", json={"heart_rate": 120})
        check("no key -> 401", r.status_code, 401)
        r = await c.post(f"{BASE}/telemetry", json={"heart_rate": 120},
                         headers={"X-Device-Key": "not-a-real-key"})
        check("bad key -> 401", r.status_code, 401)

        print("\n2. Happy path (occupied incubator)")
        r = await c.post(f"{BASE}/telemetry", headers=h1, json={
            "heart_rate": 138, "spo2": 97, "suhu_bayi": 36.8,
            "suhu_inkubator": 34.2, "kelembapan_inkubator": 62,
        })
        check("full payload -> 201", r.status_code, 201)
        check("stored flag", r.json()["stored"], True)
        rid_full = r.json()["reading_id"]

        print("\n3. The 0-means-no-reading rule")
        r = await c.post(f"{BASE}/telemetry", headers=h1, json={
            "heart_rate": 0, "spo2": 0, "suhu_bayi": 36.9,
            "suhu_inkubator": 34.1, "kelembapan_inkubator": 61,
        })
        check("probe off -> still 201", r.status_code, 201)
        rid_zero = r.json()["reading_id"]

        print("\n4. All-null payload")
        r = await c.post(f"{BASE}/telemetry", headers=h1, json={
            "heart_rate": 0, "spo2": 0, "suhu_bayi": None,
            "suhu_inkubator": None, "kelembapan_inkubator": None,
        })
        check("nothing to report -> 202", r.status_code, 202)
        check("stored flag false", r.json()["stored"], False)
        check("no reading_id", r.json()["reading_id"], None)

        print("\n5. Validation")
        r = await c.post(f"{BASE}/telemetry", headers=h1, json={"spo2": 150})
        check("spo2=150 -> 422", r.status_code, 422)
        r = await c.post(f"{BASE}/telemetry", headers=h1, json={"heart_rate": 400})
        check("hr=400 -> 422", r.status_code, 422)
        r = await c.post(f"{BASE}/telemetry", headers=h1, json={"co2_ppm": 400})
        check("unknown field -> 422", r.status_code, 422)
        r = await c.post(f"{BASE}/telemetry", headers=h1,
                         json={"ts": "2026-08-24T10:00:00Z", "heart_rate": 130})
        check("device-supplied ts rejected -> 422", r.status_code, 422)

        print("\n6. Empty incubator (no active assignment)")
        r = await c.post(f"{BASE}/telemetry", headers=h3,
                         json={"suhu_inkubator": 33.8, "kelembapan_inkubator": 58})
        check("idle unit -> 201", r.status_code, 201)
        rid_idle = r.json()["reading_id"]

    print("\n7. Database state")
    conn = await asyncpg.connect(DB)

    row = await conn.fetchrow(
        "SELECT r.*, b.baby_name FROM sensor_readings r "
        "LEFT JOIN babies b ON b.baby_id = r.baby_id WHERE reading_id=$1", rid_full)
    check("baby resolved from active assignment", row["baby_name"], "Ahmad Rizki")
    check("heart_rate stored", row["heart_rate"], 138)
    check("source", row["source"], "sensor")
    check("recorded_at set by server", row["recorded_at"] is not None, True)

    row = await conn.fetchrow("SELECT * FROM sensor_readings WHERE reading_id=$1", rid_zero)
    check("hr 0 -> NULL", row["heart_rate"], None)
    check("spo2 0 -> NULL", row["spo2"], None)
    check("temps still stored alongside", float(row["suhu_bayi"]), 36.9)

    row = await conn.fetchrow("SELECT * FROM sensor_readings WHERE reading_id=$1", rid_idle)
    check("idle unit -> baby_id NULL", row["baby_id"], None)

    dev = await conn.fetchrow("SELECT * FROM devices WHERE incubator_id=$1", INC1)

    n = await conn.fetchval(
        "SELECT COUNT(*) FROM sensor_readings WHERE device_id=$1", dev["device_id"])
    check("all-null did not insert (2 rows for this device)", n, 2)

    check("last_seen_at touched", dev["last_seen_at"] is not None, True)
    check("label stored as real UTF-8 em dash", dev["label"], "IoT device — INC-01")
    check("only the hash is stored", dev["device_key_hash"] == KEY1, False)
    check("hash length is sha256 hex", len(dev["device_key_hash"]), 64)

    audit = await conn.fetchval(
        "SELECT COUNT(*) FROM audit_logs WHERE table_name='devices' AND action='CREATE'")
    check("provisioning audited", audit >= 2, True)
    leaked = await conn.fetchval(
        "SELECT COUNT(*) FROM audit_logs WHERE details::text LIKE $1", f"%{KEY1}%")
    check("plaintext key never in audit log", leaked, 0)

    print("\n8. Unbound device (incubator record deleted out from under it)")
    await conn.execute("UPDATE devices SET incubator_id=NULL WHERE incubator_id=$1", INC3)
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.post(f"{BASE}/telemetry", headers={"X-Device-Key": KEY3},
                         json={"suhu_inkubator": 33.5})
        check("unbound device -> 409 (not 401)", r.status_code, 409)
    # Scope to THIS run's device — earlier runs leave their own orphans behind.
    import hashlib
    check(
        "device row survived with its key intact",
        await conn.fetchval(
            "SELECT COUNT(*) FROM devices WHERE device_key_hash=$1 AND incubator_id IS NULL",
            hashlib.sha256(KEY3.encode()).hexdigest()),
        1,
    )

    await conn.close()

    print(f"\n{sum(results)}/{len(results)} passed")
    return 0 if all(results) else 1


raise SystemExit(asyncio.run(main()))
