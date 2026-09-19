"""Incubator reuse and archiving: every baby's history survives both.

An incubator is used by one baby after another. This drives that life cycle end to
end through the API and checks what each screen is served at every step:

* Discharge closes the baby's own open sensor alerts ('discharged'), so the empty
  incubator stays 'kosong' and can take the next baby — before, an alert the
  departed baby left open flipped it back to 'warning' on every idle reading.
* The incubator's readings, live-stream replay, alerts and dashboard sparkline
  cover only its CURRENT occupancy; the previous baby's data is served from that
  baby instead
  (/babies/{id}/sensor-history and /alerts), including minute rollups that
  outlived the raw readings.
* A discharged baby stays reachable: GET /babies?status=pulang, full placement
  history on the detail, and a PDF that prints the admission data, not dashes.
* An incubator with history cannot be deleted but can be archived: read-only,
  device unbound, open alerts closed as 'archived', gone from dashboard and
  admission, number never reused, history still readable — and restorable.

Self-cleaning: everything it creates (one incubator, two babies, their readings,
alerts, buckets and device) is deleted at the end, except the audit log, which is
append-only by design.

Needs a LIVE backend on :8000 with LEGACY_SENSOR_INGEST enabled, and the seeded
database:

    python tests/incubator_history_check.py

Exits non-zero on any failure.
"""
import asyncio
import json
import os
import re
import sys
import zlib
from datetime import date, datetime, timedelta, timezone

import asyncpg
import httpx
from dotenv import load_dotenv

load_dotenv(".env")
DB = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
BASE = "http://localhost:8000/api/v1"
LEGACY = "http://localhost:8000/api/sensors"
PW = "Password123!"
results = []


def check(name, got, want):
    ok = got == want
    results.append((ok, name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: got {got!r}, want {want!r}")


async def login(c, email):
    r = await c.post(f"{BASE}/auth/login", json={"email": email, "password": PW})
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def pdf_text(raw: bytes) -> bytes:
    """Every decompressed content stream of an fpdf2 PDF, concatenated."""
    out = []
    for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", raw, re.S):
        try:
            out.append(zlib.decompress(m.group(1)))
        except zlib.error:
            out.append(m.group(1))
    return b"\n".join(out)


async def main():
    conn = await asyncpg.connect(DB)
    created = {"incubators": [], "babies": []}
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            A = await login(c, "admin@neonatal.rs")
            P = await login(c, "siti.aisyah@neonatal.rs")

            async def post_reading(no, **sensors):
                r = await c.post(LEGACY, json={"incubator_id": f"inc{no}", "sensors": sensors})
                return r.status_code

            async def status_of(inc_id):
                return await conn.fetchval(
                    "SELECT status::text FROM incubators WHERE incubator_id = $1", inc_id
                )

            async def register(name, inc_id):
                r = await c.post(f"{BASE}/babies", headers=P, json={
                    "baby_name": name, "gender": "perempuan",
                    "birth_date": str(date.today() - timedelta(days=2)),
                    "parent": {"mother_name": "Ibu Uji"}, "incubator_id": inc_id,
                })
                r.raise_for_status()
                created["babies"].append(r.json()["baby_id"])
                return r.json()

            print("\n1. Set-up: a fresh incubator and its first baby")
            r = await c.post(f"{BASE}/incubators", headers=A, json={"location": "CHECK riwayat"})
            check("incubator created", r.status_code, 201)
            inc = r.json()
            inc_id, no = inc["incubator_id"], inc["incubator_no"]
            created["incubators"].append(inc_id)
            baby_a = await register("Uji Riwayat A", inc_id)
            a_id = baby_a["baby_id"]
            a_reg = baby_a["current_assignment"]["no_registrasi_nicu"]
            check("incubator now terisi", await status_of(inc_id), "terisi")

            print("\n2. Baby A desaturates: three breaching readings open an alert")
            for v in (70, 69, 68):
                await post_reading(no, ds18b20_temp=36.8, spo2=v, heart_rate=150)
            check("status warning", await status_of(inc_id), "warning")
            open_a = await conn.fetch(
                "SELECT alert_id FROM sensor_alerts WHERE incubator_id=$1 AND resolved_at IS NULL", inc_id
            )
            check("one open alert, A's", len(open_a), 1)

            print("\n3. Discharge closes A's alert as 'discharged'; the empty incubator stays kosong")
            r = await c.post(f"{BASE}/babies/{a_id}/discharge", headers=P)
            check("discharge", r.status_code, 204)
            row = await conn.fetchrow(
                "SELECT s.resolved_reason, s.resolved_at = b.discharged_at AS same_time "
                "FROM sensor_alerts s JOIN baby_incubator_assignments b ON b.baby_id = s.baby_id "
                "WHERE s.alert_id = $1", open_a[0]["alert_id"],
            )
            check("closed as discharged", row["resolved_reason"], "discharged")
            check("closed at the discharge moment", row["same_time"], True)
            check("status kosong after discharge", await status_of(inc_id), "kosong")
            # Probe off the baby (no SpO2) - this used to leave A's alert open and
            # flip the empty incubator back to warning on every reading.
            for _ in range(3):
                await post_reading(no, dht22_temp=35.0, dht22_humidity=70)
            check("idle readings keep it kosong", await status_of(inc_id), "kosong")

            print("\n4. The incubator now shows only its current (empty) period")
            readings = (await c.get(f"{BASE}/incubators/{inc_id}/readings", headers=P)).json()
            check("3 idle readings served", len(readings), 3)
            check("none of them A's", all(r["baby_id"] is None for r in readings), True)
            alerts = (await c.get(f"{BASE}/incubators/{inc_id}/alerts", headers=P)).json()
            check("A's closed alert not on the incubator page", len(alerts), 0)
            dash = (await c.get(f"{BASE}/dashboard", headers=P)).json()
            card = next(i for i in dash["incubators"] if i["incubator_id"] == inc_id)
            check("sparkline carries none of A's 36.8", 36.8 in card["sparkline"], False)

            print("\n5. Baby B takes the same incubator")
            baby_b = await register("Uji Riwayat B", inc_id)
            b_id = baby_b["baby_id"]
            await post_reading(no, ds18b20_temp=37.1, spo2=97, heart_rate=140)
            readings = (await c.get(f"{BASE}/incubators/{inc_id}/readings", headers=P)).json()
            check("incubator readings are B's only", [r["baby_id"] for r in readings], [b_id])
            latest = (await c.get(f"{BASE}/babies/{b_id}/latest-reading", headers=P)).json()
            check("B's autofill is B's reading", latest and latest["suhu_bayi"], 37.1)
            # The live stream replays an in-memory buffer that holds A's readings
            # too; it must start at B's admission like /readings does.
            replayed = []
            try:
                async with c.stream("GET", f"{BASE}/incubators/{inc_id}/stream", headers=P,
                                    timeout=httpx.Timeout(3.0)) as s:
                    async for line in s.aiter_lines():
                        if line.startswith("data: "):
                            replayed.append(json.loads(line[6:])["baby_id"])
            except httpx.ReadTimeout:
                pass  # replay done; the stream then idles until the next reading
            check("stream replay holds B's reading only", replayed, [b_id])

            print("\n6. A's history is served from A - raw readings plus minute rollups")
            # This script runs inside a minute, but a rollup bucket covers one
            # incubator-minute whoever was in it. Move A's raw rows ten minutes back
            # so the bucket planted below does not also swallow B's reading.
            await conn.execute(
                "UPDATE sensor_readings SET recorded_at = recorded_at - interval '10 minutes' "
                "WHERE baby_id = $1", a_id,
            )
            now = datetime.now(timezone.utc)
            # An hour-old bucket stands in for data whose raw rows were pruned.
            old_minute = (now - timedelta(hours=1)).replace(second=0, microsecond=0)
            await conn.execute(
                "INSERT INTO sensor_reading_minutes (incubator_id, baby_id, minute, sample_count, "
                "spo2_avg, spo2_min, spo2_max) VALUES ($1, $2, $3, 20, 80, 55, 95)",
                inc_id, a_id, old_minute,
            )
            # A bucket for a minute that ALSO still has raw rows must win, not add up.
            raw_minute = await conn.fetchval(
                "SELECT date_trunc('minute', min(recorded_at)) FROM sensor_readings WHERE baby_id=$1", a_id
            )
            await conn.execute(
                "INSERT INTO sensor_reading_minutes (incubator_id, baby_id, minute, sample_count, "
                "spo2_avg, spo2_min, spo2_max) VALUES ($1, $2, $3, 7, 69, 68, 70)",
                inc_id, a_id, raw_minute,
            )
            raw_elsewhere = await conn.fetchval(
                "SELECT count(*) FROM sensor_readings WHERE baby_id=$1 "
                "AND date_trunc('minute', recorded_at) <> $2", a_id, raw_minute,
            )
            hist = (await c.get(f"{BASE}/babies/{a_id}/sensor-history", headers=P)).json()
            total = sum(p["samples"] for p in hist["points"])
            check("samples = buckets + raw rows not yet rolled up", total, 20 + 7 + raw_elsewhere)
            check("the pruned-era minimum survives", min(p["spo2_min"] for p in hist["points"] if p["spo2_min"] is not None), 55.0)
            check("hour-long span stays at 1-minute buckets", hist["bucket_minutes"], 1)
            check("numbers, not strings", isinstance(hist["points"][0]["samples"], int), True)
            # A month-long stay must come back bucketed, not as 43 200 rows.
            await conn.execute(
                "INSERT INTO sensor_reading_minutes (incubator_id, baby_id, minute, sample_count, spo2_avg) "
                "VALUES ($1, $2, $3, 20, 96)",
                inc_id, a_id, old_minute - timedelta(days=30),
            )
            hist = (await c.get(f"{BASE}/babies/{a_id}/sensor-history", headers=P)).json()
            check("30-day span widened to 73-minute buckets", hist["bucket_minutes"], 73)
            check("at most 600 points", len(hist["points"]) <= 600, True)
            a_alerts = (await c.get(f"{BASE}/babies/{a_id}/alerts", headers=P)).json()
            check("A's alert is on A", len(a_alerts), 1)
            check("... marked discharged", a_alerts[0]["resolved_reason"], "discharged")
            check("... with its incubator number", a_alerts[0]["incubator_no"], no)
            b_hist = (await c.get(f"{BASE}/babies/{b_id}/sensor-history", headers=P)).json()
            check("B's history holds B's one reading", sum(p["samples"] for p in b_hist["points"]), 1)

            print("\n7. A discharged baby stays reachable, with admission data intact")
            detail = (await c.get(f"{BASE}/babies/{a_id}", headers=P)).json()
            check("A inactive", detail["is_active"], False)
            check("no current placement", detail["current_assignment"], None)
            check("one placement kept", len(detail["placements"]), 1)
            check("... in this incubator", detail["placements"][0]["incubator_no"], no)
            check("... discharged", detail["placements"][0]["status"], "discharged")
            check("... with a discharge time", detail["placements"][0]["discharged_at"] is not None, True)
            report = (await c.get(f"{BASE}/babies/{a_id}/report", headers=P)).json()
            check("report carries the placement", report["baby"]["placements"][0]["no_registrasi_nicu"], a_reg)
            r = await c.get(f"{BASE}/babies/{a_id}/report/pdf", headers=P)
            text = pdf_text(r.content)
            check("PDF generated", r.status_code, 200)
            check("PDF prints the registration number", a_reg.encode() in text, True)
            check("PDF prints the incubator", f"No. {no}".encode() in text, True)
            check("PDF says discharged", b"Sudah pulang" in text, True)

            def ids(rows):
                return {b["baby_id"] for b in rows}
            pulang = (await c.get(f"{BASE}/babies", headers=P, params={"status": "pulang", "q": "Uji Riwayat"})).json()
            check("status=pulang lists A, not B", (a_id in ids(pulang), b_id in ids(pulang)), (True, False))
            item = next(b for b in pulang if b["baby_id"] == a_id)
            check("... with A's last placement", item["placement"]["incubator_no"], no)
            aktif = (await c.get(f"{BASE}/babies", headers=P, params={"q": "Uji Riwayat"})).json()
            check("default (aktif) lists B, not A", (b_id in ids(aktif), a_id in ids(aktif)), (True, False))
            semua = (await c.get(f"{BASE}/babies", headers=P, params={"status": "semua", "q": a_reg})).json()
            check("search by NICU registration number finds A", ids(semua), {a_id})

            placements = (await c.get(f"{BASE}/incubators/{inc_id}/placements", headers=P)).json()
            check("usage history: B then A",
                  [(p["baby_id"], p["status"]) for p in placements],
                  [(b_id, "active"), (a_id, "discharged")])

            print("\n8. Archive is refused while a baby is inside, and never for non-admins")
            r = await c.post(f"{BASE}/incubators/{inc_id}/archive", headers=A)
            check("archive with B inside", r.status_code, 409)
            r = await c.post(f"{BASE}/incubators/{inc_id}/archive", headers=P)
            check("perawat may not archive", r.status_code, 403)

            print("\n9. Archiving the emptied incubator")
            r = await c.post(f"{BASE}/incubators/{inc_id}/device", headers=A, json={"label": "CHECK rig"})
            check("device provisioned (to be unbound)", r.status_code, 201)
            await c.post(f"{BASE}/babies/{b_id}/discharge", headers=P)
            r = await c.delete(f"{BASE}/incubators/{inc_id}", headers=A)
            check("empty but used: delete refused", r.status_code, 409)
            check("... pointing at archive", "Arsipkan" in r.json()["detail"], True)
            for _ in range(3):  # the empty incubator's own air-temperature alarm
                await post_reading(no, dht22_temp=30.0)
            check("empty incubator alarms on air temperature", await status_of(inc_id), "warning")
            r = await c.post(f"{BASE}/incubators/{inc_id}/archive", headers=A)
            check("archive", r.status_code, 200)
            body = r.json()
            check("archived_at set", body["archived_at"] is not None, True)
            check("status tidak_tersedia", body["status"], "tidak_tersedia")
            check("has_history", body["has_history"], True)
            dev = (await c.get(f"{BASE}/incubators/{inc_id}/device", headers=A)).json()
            check("device unbound", dev, None)
            reasons = await conn.fetch(
                "SELECT resolved_reason FROM sensor_alerts WHERE incubator_id=$1 AND baby_id IS NULL", inc_id
            )
            check("air-temp alarm closed as archived", [r["resolved_reason"] for r in reasons], ["archived"])
            check("nothing left open",
                  await conn.fetchval("SELECT count(*) FROM sensor_alerts WHERE incubator_id=$1 AND resolved_at IS NULL", inc_id), 0)

            print("\n10. Gone from service, still readable")
            active_ids = {i["incubator_id"] for i in (await c.get(f"{BASE}/incubators", headers=P)).json()}
            check("not in the incubator list", inc_id in active_ids, False)
            archived_ids = {i["incubator_id"] for i in (await c.get(f"{BASE}/incubators", headers=P, params={"archived": "true"})).json()}
            check("in the archive list", inc_id in archived_ids, True)
            avail = {i["incubator_id"] for i in (await c.get(f"{BASE}/incubators/available", headers=P)).json()}
            check("not offered for admission", inc_id in avail, False)
            dash = (await c.get(f"{BASE}/dashboard", headers=P)).json()
            check("not on the dashboard", any(i["incubator_id"] == inc_id for i in dash["incubators"]), False)
            check("not counted in the stats", dash["stats"]["total"], len(dash["incubators"]))
            check("detail still readable", (await c.get(f"{BASE}/incubators/{inc_id}", headers=P)).status_code, 200)
            check("usage history still readable", len((await c.get(f"{BASE}/incubators/{inc_id}/placements", headers=P)).json()), 2)
            check("A's history untouched",
                  sum(p["samples"] for p in (await c.get(f"{BASE}/babies/{a_id}/sensor-history", headers=P)).json()["points"]) > 0, True)

            print("\n11. Read-only while archived")
            check("status change", (await c.put(f"{BASE}/incubators/{inc_id}", headers=A, json={"status": "kosong"})).status_code, 409)
            check("thresholds", (await c.put(f"{BASE}/incubators/{inc_id}/thresholds", headers=A, json={"thresholds": {}})).status_code, 409)
            check("device", (await c.post(f"{BASE}/incubators/{inc_id}/device", headers=A, json={})).status_code, 409)
            check("telemetry", await post_reading(no, dht22_temp=35.0), 409)
            r = await c.post(f"{BASE}/babies", headers=P, json={
                "baby_name": "Uji Riwayat C", "gender": "laki_laki", "birth_date": str(date.today()),
                "parent": {}, "incubator_id": inc_id,
            })
            check("admission", r.status_code, 409)
            check("archive twice", (await c.post(f"{BASE}/incubators/{inc_id}/archive", headers=A)).status_code, 409)

            print("\n12. Its number is never handed out again")
            r = await c.post(f"{BASE}/incubators", headers=A, json={"location": "CHECK nomor"})
            nxt = r.json()
            created["incubators"].append(nxt["incubator_id"])
            check("next number skips the archived one", nxt["incubator_no"], f"{int(no) + 1:02d}")
            check("unused incubator still deletes outright",
                  (await c.delete(f"{BASE}/incubators/{nxt['incubator_id']}", headers=A)).status_code, 204)
            created["incubators"].remove(nxt["incubator_id"])

            print("\n13. Restore")
            check("perawat may not restore", (await c.post(f"{BASE}/incubators/{inc_id}/restore", headers=P)).status_code, 403)
            r = await c.post(f"{BASE}/incubators/{inc_id}/restore", headers=A)
            check("restore", r.status_code, 200)
            check("archived_at cleared", r.json()["archived_at"], None)
            check("returns as tidak_tersedia, not bookable", r.json()["status"], "tidak_tersedia")
            active_ids = {i["incubator_id"] for i in (await c.get(f"{BASE}/incubators", headers=P)).json()}
            check("back in the list", inc_id in active_ids, True)
            check("restore twice", (await c.post(f"{BASE}/incubators/{inc_id}/restore", headers=A)).status_code, 409)

            logs = (await c.get(f"{BASE}/audit-logs", headers=A, params={"limit": 100})).json()
            actions = {l["action"] for l in logs if str(l.get("record_id")) == inc_id}
            check("ARCHIVE and RESTORE audited", {"ARCHIVE", "RESTORE"} <= actions, True)
    finally:
        # Leave the seeded database as it was found (bar the append-only audit log).
        for inc_id in created["incubators"]:
            for t in ("sensor_alerts", "sensor_readings", "sensor_reading_minutes", "devices"):
                await conn.execute(f"DELETE FROM {t} WHERE incubator_id = $1", inc_id)
        for b in created["babies"]:
            await conn.execute("DELETE FROM baby_incubator_assignments WHERE baby_id = $1", b)
            await conn.execute("DELETE FROM parents WHERE baby_id = $1", b)
            await conn.execute("DELETE FROM maternal_records WHERE baby_id = $1", b)
            await conn.execute("DELETE FROM babies WHERE baby_id = $1", b)
        for inc_id in created["incubators"]:
            await conn.execute("DELETE FROM incubators WHERE incubator_id = $1", inc_id)
        await conn.close()

    passed = sum(1 for ok, _ in results if ok)
    print(f"\n{passed}/{len(results)} passed")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    asyncio.run(main())
