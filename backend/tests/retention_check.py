"""P4 acceptance: sensor retention (rollup + prune).

Plain asserts, no framework. Talks to the database directly rather than through
the API, because retention is a background job with no HTTP surface.

Self-cleaning: works on INC-03 (empty) and removes everything it created.

    python tests/retention_check.py

Exits non-zero on any failure.
"""
import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

load_dotenv(".env")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services import retention_service  # noqa: E402

INC3 = "bbbbbbbb-0002-0002-0002-000000000003"
results = []


def check(name, got, want):
    ok = got == want
    results.append((ok, name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: got {got!r}, want {want!r}")


async def main():
    engine = create_async_engine(os.environ["DATABASE_URL"], echo=False)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as db:
        await db.execute(
            text("DELETE FROM sensor_reading_minutes WHERE incubator_id = :i"),
            {"i": INC3},
        )
        await db.execute(
            text("DELETE FROM sensor_readings WHERE incubator_id = :i"), {"i": INC3}
        )
        await db.commit()

        now = datetime.now(timezone.utc)
        # Anchored to a minute boundary so the bucket maths is deterministic:
        # 40 readings x 3 s from :00 is exactly two full minutes of 20 samples.
        # Starting mid-minute would straddle three buckets and make the expected
        # counts depend on what time the test happened to run.
        old = (now - timedelta(days=10)).replace(second=0, microsecond=0)
        fresh = now - timedelta(minutes=5)

        print("\n1. Seed: 40 old readings across 2 minutes, plus 5 fresh ones")
        for i in range(40):
            ts = old + timedelta(seconds=3 * i)  # spans 2 minutes
            await db.execute(
                text(
                    "INSERT INTO sensor_readings "
                    "(incubator_id, recorded_at, suhu_bayi, heart_rate, spo2, source) "
                    "VALUES (:i, :t, :temp, :hr, :sp, 'sensor')"
                ),
                {"i": INC3, "t": ts, "temp": 36.0 + (i % 5) * 0.1,
                 "hr": 120 + (i % 10), "sp": 95 + (i % 5)},
            )
        for i in range(5):
            await db.execute(
                text(
                    "INSERT INTO sensor_readings "
                    "(incubator_id, recorded_at, suhu_bayi, source) "
                    "VALUES (:i, :t, 36.5, 'sensor')"
                ),
                {"i": INC3, "t": fresh + timedelta(seconds=3 * i)},
            )
        await db.commit()

        async def raw_count():
            return await db.scalar(
                text("SELECT count(*) FROM sensor_readings WHERE incubator_id = :i"),
                {"i": INC3},
            )

        async def bucket_count():
            return await db.scalar(
                text("SELECT count(*) FROM sensor_reading_minutes WHERE incubator_id = :i"),
                {"i": INC3},
            )

        check("45 raw readings seeded", await raw_count(), 45)

        print("\n2. Retention run (7-day window)")
        res = await retention_service.run_retention(db, retention_days=7, now=now)
        check("buckets written", res["buckets"], 2)
        check("raw rows pruned", res["pruned"], 40)
        check("fresh readings untouched", await raw_count(), 5)
        check("two minute buckets kept", await bucket_count(), 2)

        print("\n3. min/max survive — an excursion must not be averaged away")
        row = (
            await db.execute(
                text(
                    "SELECT sample_count, heart_rate_min, heart_rate_max, heart_rate_avg, "
                    "spo2_min, spo2_max FROM sensor_reading_minutes "
                    "WHERE incubator_id = :i ORDER BY minute LIMIT 1"
                ),
                {"i": INC3},
            )
        ).first()
        check("sample_count recorded", row.sample_count, 20)
        check("hr min preserved", float(row.heart_rate_min), 120.0)
        check("hr max preserved", float(row.heart_rate_max), 129.0)
        check("hr avg between them", 120.0 < float(row.heart_rate_avg) < 129.0, True)
        check("spo2 min preserved", float(row.spo2_min), 95.0)
        check("spo2 max preserved", float(row.spo2_max), 99.0)

        print("\n4. Idempotent — a re-run must not duplicate buckets")
        res2 = await retention_service.run_retention(db, retention_days=7, now=now)
        check("still two buckets", await bucket_count(), 2)
        check("nothing left to prune", res2["pruned"], 0)

        print("\n5. Prune never runs ahead of the rollup")
        # Raw rows whose minute has NO bucket must survive a prune, so a failed
        # rollup degrades to a big table rather than to lost history.
        orphan = now - timedelta(days=30)
        await db.execute(
            text(
                "INSERT INTO sensor_readings (incubator_id, recorded_at, suhu_bayi, source) "
                "VALUES (:i, :t, 36.5, 'sensor')"
            ),
            {"i": INC3, "t": orphan},
        )
        await db.commit()
        pruned = await retention_service.prune(db, before=now)
        await db.commit()
        survived = await db.scalar(
            text(
                "SELECT count(*) FROM sensor_readings "
                "WHERE incubator_id = :i AND recorded_at = :t"
            ),
            {"i": INC3, "t": orphan},
        )
        check("unrolled row was NOT deleted", survived, 1)
        check("prune reported deleting nothing", pruned, 0)

        print("\n6. retention_days <= 0 keeps everything")
        before = await raw_count()
        res3 = await retention_service.run_retention(db, retention_days=0, now=now)
        check("run skipped", res3["skipped"], 1)
        check("no rows removed", await raw_count(), before)

        print("\n7. Cleanup")
        await db.execute(
            text("DELETE FROM sensor_reading_minutes WHERE incubator_id = :i"), {"i": INC3}
        )
        await db.execute(
            text("DELETE FROM sensor_readings WHERE incubator_id = :i"), {"i": INC3}
        )
        await db.commit()
        check("cleaned up", await raw_count(), 0)

    await engine.dispose()

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
