"""P2 acceptance: SSE fan-out from POST /telemetry to GET /incubators/{id}/stream.

Plain asserts, no framework — same spirit as telemetry_check.py.

Self-cleaning: provisions a throwaway device on INC-03 (an empty incubator),
streams from it, and revokes the device at the end. The readings it ingests stay,
which is correct — they are real rows and revoking a device never deletes history.

Needs a LIVE backend on :8000 and the seeded dev database:

    python -m uvicorn app.main:app --port 8000     # in one shell
    python tests/stream_check.py                   # in another

Exits non-zero on any failure.
"""
import asyncio
import json
import sys

import httpx

BASE = "http://localhost:8000/api/v1"
ADMIN = {"email": "admin@neonatal.rs", "password": "Password123!"}
INC3 = "bbbbbbbb-0002-0002-0002-000000000003"  # kosong

results = []


def check(name, got, want):
    ok = got == want
    results.append((ok, name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: got {got!r}, want {want!r}")


async def read_frames(resp, stop: asyncio.Event, frames: list):
    """Collect `data:` payloads until told to stop."""
    buf = ""
    async for chunk in resp.aiter_text():
        buf += chunk
        while "\n\n" in buf:
            raw, buf = buf.split("\n\n", 1)
            for line in raw.splitlines():
                if line.startswith("data: "):
                    frames.append(json.loads(line[6:]))
                elif line.startswith(":"):
                    frames.append({"__ping__": True})
        if stop.is_set():
            return


async def main():
    async with httpx.AsyncClient(timeout=30) as c:
        token = (await c.post(f"{BASE}/auth/login", json=ADMIN)).json()["access_token"]
        auth = {"Authorization": f"Bearer {token}"}

        print("\n1. Provision a throwaway device on INC-03")
        await c.delete(f"{BASE}/incubators/{INC3}/device", headers=auth)
        r = await c.post(f"{BASE}/incubators/{INC3}/device", headers=auth, json={})
        check("provision -> 201", r.status_code, 201)
        key = r.json()["device_key"]

        print("\n2. Stream headers")
        frames: list = []
        stop = asyncio.Event()
        async with c.stream(
            "GET", f"{BASE}/incubators/{INC3}/stream", headers=auth
        ) as resp:
            check("stream -> 200", resp.status_code, 200)
            check(
                "content-type is event-stream",
                resp.headers["content-type"].startswith("text/event-stream"),
                True,
            )
            check("x-accel-buffering disabled", resp.headers.get("x-accel-buffering"), "no")

            reader = asyncio.create_task(read_frames(resp, stop, frames))
            await asyncio.sleep(0.4)  # let the subscriber register

            print("\n3. A reading ingested now must reach the open stream")
            post = await c.post(
                f"{BASE}/telemetry",
                headers={"X-Device-Key": key},
                json={"suhu_bayi": 36.4, "heart_rate": 141, "spo2": 97},
            )
            check("ingest -> 201", post.status_code, 201)
            reading_id = post.json()["reading_id"]

            for _ in range(50):          # up to ~5 s
                if any(f.get("reading_id") == reading_id for f in frames):
                    break
                await asyncio.sleep(0.1)

            stop.set()
            got = next((f for f in frames if f.get("reading_id") == reading_id), None)
            check("reading arrived on the stream", got is not None, True)
            if got:
                check("suhu_bayi carried through", float(got["suhu_bayi"]), 36.4)
                check("heart_rate carried through", got["heart_rate"], 141)
                check("baby_id null on an empty incubator", got["baby_id"], None)

            print("\n4. Null semantics survive the stream")
            post2 = await c.post(
                f"{BASE}/telemetry",
                headers={"X-Device-Key": key},
                json={"suhu_bayi": 36.5, "heart_rate": 0, "spo2": 0},
            )
            rid2 = post2.json()["reading_id"]
            for _ in range(50):
                if any(f.get("reading_id") == rid2 for f in frames):
                    break
                await asyncio.sleep(0.1)
            got2 = next((f for f in frames if f.get("reading_id") == rid2), None)
            check("second reading streamed", got2 is not None, True)
            if got2:
                check("hr 0 -> null over the wire", got2["heart_rate"], None)
                check("spo2 0 -> null over the wire", got2["spo2"], None)

            reader.cancel()

        print("\n5. Replay: a NEW subscriber gets recent history immediately")
        replayed: list = []
        stop2 = asyncio.Event()
        async with c.stream(
            "GET", f"{BASE}/incubators/{INC3}/stream", headers=auth
        ) as resp2:
            reader2 = asyncio.create_task(read_frames(resp2, stop2, replayed))
            await asyncio.sleep(1.0)
            stop2.set()
            reader2.cancel()
        ids = {f.get("reading_id") for f in replayed}
        check("buffer replayed to a fresh subscriber", reading_id in ids, True)

        print("\n6. Cleanup")
        rv = await c.delete(f"{BASE}/incubators/{INC3}/device", headers=auth)
        check("revoke -> 204", rv.status_code, 204)

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
