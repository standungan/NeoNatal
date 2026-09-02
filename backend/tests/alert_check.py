"""P4 acceptance: the threshold alert engine.

Plain asserts, no framework — same spirit as telemetry_check.py.

Drives the engine through the REAL ingest path (POST /api/sensors on a spare
incubator) so debounce, status flipping and recovery are exercised exactly as
they happen in production, not against a mocked service.

Self-cleaning: uses INC-03 (empty), and deletes the readings and alerts it
created at the end so the seeded database is left as it was found.

Needs a LIVE backend on :8000 with LEGACY_SENSOR_INGEST enabled, and the seeded
database:

    python -m uvicorn app.main:app --port 8000     # in one shell
    python tests/alert_check.py                    # in another

Exits non-zero on any failure.
"""
import asyncio
import os
import sys

import asyncpg
import httpx
from dotenv import load_dotenv

load_dotenv(".env")
DB = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
BASE = "http://localhost:8000/api/v1"
LEGACY = "http://localhost:8000/api/sensors"
INC3 = "bbbbbbbb-0002-0002-0002-000000000003"  # kosong — no baby to disturb
INC5 = "bbbbbbbb-0002-0002-0002-000000000005"  # terisi (Hana Putri) — needed to
#                                                exercise monitoring_service, which
#                                                only touches status when a baby is assigned
ADMIN = {"email": "admin@neonatal.rs", "password": "Password123!"}

results = []


def check(name, got, want):
    ok = got == want
    results.append((ok, name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: got {got!r}, want {want!r}")


async def post(c, *, suhu=None, hr=None, spo2=None):
    sensors = {}
    if suhu is not None:
        sensors["ds18b20_temp"] = suhu
    if hr is not None:
        sensors["heart_rate"] = hr
    if spo2 is not None:
        sensors["spo2"] = spo2
    r = await c.post(LEGACY, json={"incubator_id": "inc3", "sensors": sensors})
    return r.status_code


async def open_alerts(conn):
    return await conn.fetch(
        "SELECT alert_type, metric_key, value, threshold FROM sensor_alerts "
        "WHERE incubator_id = $1 AND resolved_at IS NULL ORDER BY alert_type",
        INC3,
    )


async def status(conn):
    return await conn.fetchval(
        "SELECT status::text FROM incubators WHERE incubator_id = $1", INC3
    )


async def main():
    conn = await asyncpg.connect(DB)
    async with httpx.AsyncClient(timeout=20) as c:
        # clean slate
        await conn.execute("DELETE FROM sensor_alerts WHERE incubator_id = $1", INC3)
        await conn.execute("DELETE FROM sensor_readings WHERE incubator_id = $1", INC3)
        await conn.execute(
            "UPDATE incubators SET status = 'kosong' WHERE incubator_id = $1", INC3
        )

        thr = await conn.fetchval(
            "SELECT alert_thresholds FROM incubators WHERE incubator_id = $1", INC3
        )
        print(f"\n  (incubator thresholds: {'custom' if thr else 'defaults'})")

        print("\n1. One breaching reading must NOT open an alert (debounce)")
        check("ingest accepted", await post(c, spo2=70), 201)
        check("no alert after 1 breach", len(await open_alerts(conn)), 0)
        check("status untouched", await status(conn), "kosong")

        print("\n2. Two is still not enough")
        await post(c, spo2=70)
        check("no alert after 2 breaches", len(await open_alerts(conn)), 0)

        print("\n3. The third consecutive breach opens it")
        await post(c, spo2=70)
        rows = await open_alerts(conn)
        check("one alert open", len(rows), 1)
        if rows:
            check("type is desaturation", rows[0]["alert_type"], "desaturation")
            check("metric recorded", rows[0]["metric_key"], "spo2")
            check("breaching value captured", float(rows[0]["value"]), 70.0)
        check("incubator flipped to warning", await status(conn), "warning")

        print("\n4. A further breach refreshes, never duplicates")
        await post(c, spo2=68)
        check("still exactly one open alert", len(await open_alerts(conn)), 1)

        print("\n5. Nulls neither open nor resolve — a probe that is off proves nothing")
        for _ in range(3):
            await post(c, spo2=0)  # 0 is normalised to NULL on ingest
        check("alert still open through nulls", len(await open_alerts(conn)), 1)
        check("status still warning", await status(conn), "warning")

        print("\n6. Three in-range readings resolve it")
        await post(c, spo2=97)
        check("one reading back in range is not enough", len(await open_alerts(conn)), 1)
        await post(c, spo2=97)
        await post(c, spo2=97)
        check("alert resolved", len(await open_alerts(conn)), 0)
        check(
            "status restored to kosong (empty incubator, not terisi)",
            await status(conn),
            "kosong",
        )

        print("\n7. Resolution is recorded, not deleted")
        total = await conn.fetchval(
            "SELECT count(*) FROM sensor_alerts WHERE incubator_id = $1", INC3
        )
        check("the episode is kept as history", total, 1)
        resolved = await conn.fetchval(
            "SELECT resolved_at IS NOT NULL FROM sensor_alerts WHERE incubator_id = $1",
            INC3,
        )
        check("resolved_at set", resolved, True)

        print("\n8. A metric with no producer can never alarm")
        # respiratory_rate has no sensor; even a wild value must stay silent.
        await conn.execute(
            "INSERT INTO sensor_readings (incubator_id, respiratory_rate, source) "
            "VALUES ($1, 999, 'sensor'), ($1, 999, 'sensor'), ($1, 999, 'sensor')",
            INC3,
        )
        await post(c, suhu=36.5)
        types = [r["alert_type"] for r in await open_alerts(conn)]
        check("no apnea/respiratory alert raised", "apnea" in types, False)

        print("\n9. A warning raised by someone else must survive")
        # 'warning' has three producers: this engine, an observation item
        # scored 0, and a manual vitals entry. A warning with no open sensor
        # alert is somebody else's clinical flag, and in-range telemetry must
        # not clear it.
        await conn.execute(
            "UPDATE incubators SET status = 'warning' WHERE incubator_id = $1", INC3
        )
        for _ in range(4):
            await post(c, spo2=98, suhu=36.5)
        check("another module's warning is left alone", await status(conn), "warning")
        check(
            "and no sensor alert was invented to justify it",
            len(await open_alerts(conn)),
            0,
        )

        print("\n10. Normal manual vitals must not dismiss a live sensor alert")
        # The reverse of step 9: monitoring_service downgrades warning->terisi on
        # a normal entry. With a sensor alert open that would let a nurse charting
        # a normal reading silently clear the sensor's alarm.
        # Uses an OCCUPIED incubator — monitoring only touches status when a baby
        # is assigned, so running this on an empty one proves nothing.
        await conn.execute("DELETE FROM sensor_alerts WHERE incubator_id = $1", INC5)
        await conn.execute("DELETE FROM sensor_readings WHERE incubator_id = $1", INC5)
        inc5_status_before = await conn.fetchval(
            "SELECT status::text FROM incubators WHERE incubator_id = $1", INC5
        )

        for _ in range(3):
            r = await c.post(
                LEGACY, json={"incubator_id": "inc5", "sensors": {"spo2": 70}}
            )
        open5 = await conn.fetch(
            "SELECT alert_id FROM sensor_alerts WHERE incubator_id = $1 "
            "AND resolved_at IS NULL", INC5
        )
        check("alert raised on the occupied incubator", len(open5), 1)
        check(
            "status is warning",
            await conn.fetchval(
                "SELECT status::text FROM incubators WHERE incubator_id = $1", INC5
            ),
            "warning",
        )

        tok = (await c.post(f"{BASE}/auth/login", json=ADMIN)).json()["access_token"]
        h = {"Authorization": f"Bearer {tok}"}
        baby5 = await conn.fetchval(
            "SELECT baby_id FROM baby_incubator_assignments "
            "WHERE incubator_id = $1 AND status = 'active' LIMIT 1", INC5
        )
        check("a baby IS assigned (otherwise this step proves nothing)", baby5 is not None, True)

        r = await c.post(
            f"{BASE}/babies/{baby5}/monitoring", headers=h,
            json={"heart_rate": 130, "spo2": 98, "suhu_bayi": 36.8,
                  "observation_time": "2026-09-02T10:00:00Z"},
        )
        check("normal manual vitals accepted", r.status_code in (200, 201), True)
        check(
            "sensor alert NOT dismissed by the manual entry",
            await conn.fetchval(
                "SELECT status::text FROM incubators WHERE incubator_id = $1", INC5
            ),
            "warning",
        )
        check(
            "and the alert row is still open",
            await conn.fetchval(
                "SELECT count(*) FROM sensor_alerts WHERE incubator_id = $1 "
                "AND resolved_at IS NULL", INC5
            ),
            1,
        )

        # restore INC-05 exactly as found
        await conn.execute("DELETE FROM sensor_alerts WHERE incubator_id = $1", INC5)
        await conn.execute("DELETE FROM sensor_readings WHERE incubator_id = $1", INC5)
        await conn.execute(
            "DELETE FROM monitoring_records WHERE baby_id = $1 "
            "AND observation_time = '2026-09-02T10:00:00Z'", baby5
        )
        await conn.execute(
            "UPDATE incubators SET status = $2::incubator_status WHERE incubator_id = $1",
            INC5, inc5_status_before,
        )
        check(
            "INC-05 restored",
            await conn.fetchval(
                "SELECT status::text FROM incubators WHERE incubator_id = $1", INC5
            ),
            inc5_status_before,
        )

        print("\n11. Cleanup")
        await conn.execute("DELETE FROM sensor_alerts WHERE incubator_id = $1", INC3)
        await conn.execute("DELETE FROM sensor_readings WHERE incubator_id = $1", INC3)
        await conn.execute(
            "UPDATE incubators SET status = 'kosong' WHERE incubator_id = $1", INC3
        )
        check("readings cleaned up", await conn.fetchval(
            "SELECT count(*) FROM sensor_readings WHERE incubator_id = $1", INC3), 0)

    await conn.close()

    passed = sum(1 for ok, _ in results if ok)
    total = len(results)
    print(f"\n{passed}/{total} passed")
    if passed != total:
        print("\nFailures:")
        for ok, name in results:
            if not ok:
                print("  -", name)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
