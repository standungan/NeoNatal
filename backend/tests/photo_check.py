"""Monitoring photos: upload, read back behind a session, and print in the report.

A photo of a patient is a clinical read, so it is served by
GET /api/v1/monitoring/{id}/photo — gated like everything else — and no longer from an
open /uploads directory. The PDF carries every photo on the record, re-encoded small.

Self-cleaning: creates ONE monitoring record on a seeded baby, attaches a photo, and
deletes both at the end. It picks a baby whose incubator is already 'terisi' and charts
normal vitals, so no incubator status changes. Audit rows stay, by design.

Needs a LIVE backend on :8000 and the seeded database:

    python tests/photo_check.py

Exits non-zero on any failure.
"""
import asyncio
import io
import os
import re
import sys
import uuid
import zlib
from datetime import datetime, timezone

import asyncpg
import httpx
from dotenv import load_dotenv
from PIL import Image

load_dotenv(".env")
DB = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
BASE = "http://localhost:8000/api/v1"
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


def sample_jpeg(px: int = 1400) -> bytes:
    """A photo-sized JPEG, big enough that the thumbnail must actually shrink it."""
    img = Image.new("RGB", (px, int(px * 0.75)))
    for y in range(img.height):          # a gradient compresses to a realistic size
        for x in range(0, img.width, 8):
            img.putpixel((x, y), ((x * 255) // img.width, (y * 255) // img.height, 160))
    out = io.BytesIO()
    img.save(out, "JPEG", quality=90)
    return out.getvalue()


def pdf_text(raw: bytes) -> bytes:
    out = []
    for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", raw, re.S):
        try:
            out.append(zlib.decompress(m.group(1)))
        except zlib.error:
            pass
    return b"\n".join(out)


async def main():
    conn = await asyncpg.connect(DB)
    monitoring_id = None
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            A = await login(c, "admin@neonatal.rs")
            P = await login(c, "siti.aisyah@neonatal.rs")
            D = await login(c, "dr.anisa@neonatal.rs")

            incs = (await c.get(f"{BASE}/incubators", headers=P)).json()
            occupied = next(i for i in incs if i["status"] == "terisi" and i["current_baby"])
            baby_id = occupied["current_baby"]["baby_id"]

            print("\n1. A monitoring record starts without a photo")
            r = await c.post(f"{BASE}/babies/{baby_id}/monitoring", headers=P, json={
                "observation_time": datetime.now(timezone.utc).isoformat(),
                "suhu_bayi": 36.8, "heart_rate": 140, "spo2": 97, "respiratory_rate": 45,
                "catatan": "CHECK foto",
            })
            check("record created", r.status_code, 201)
            monitoring_id = r.json()["monitoring_id"]
            check("no photo yet", r.json()["foto_url"], None)
            check("reading it 404s",
                  (await c.get(f"{BASE}/monitoring/{monitoring_id}/photo", headers=P)).status_code, 404)

            print("\n2. Upload")
            original = sample_jpeg()
            files = {"file": ("foto.jpg", original, "image/jpeg")}
            check("dokter may not upload",
                  (await c.post(f"{BASE}/monitoring/{monitoring_id}/photo", headers=D,
                                files={"file": ("foto.jpg", original, "image/jpeg")})).status_code, 403)
            r = await c.post(f"{BASE}/monitoring/{monitoring_id}/photo", headers=P, files=files)
            check("perawat uploads", r.status_code, 200)
            check("stored under the baby", r.json()["foto_url"].startswith(f"/uploads/{baby_id}/"), True)
            foto_url = r.json()["foto_url"]

            print("\n3. Reading it needs a session, and is not a static file any more")
            check("no token -> refused",
                  (await c.get(f"{BASE}/monitoring/{monitoring_id}/photo")).status_code, 403)
            check("the old static path is gone",
                  (await c.get(f"http://localhost:8000{foto_url}")).status_code, 404)
            r = await c.get(f"{BASE}/monitoring/{monitoring_id}/photo", headers=D)
            check("dokter may read it", r.status_code, 200)
            check("bytes are the file as uploaded", r.content == original, True)
            check("content type", r.headers["content-type"], "image/jpeg")
            check("not cached by shared caches", "private" in r.headers.get("cache-control", ""), True)

            print("\n4. Thumbnail")
            r = await c.get(f"{BASE}/monitoring/{monitoring_id}/photo", headers=P, params={"thumb": "true"})
            check("thumb served", r.status_code, 200)
            thumb = Image.open(io.BytesIO(r.content))
            check("thumb is a JPEG", thumb.format, "JPEG")
            check("no bigger than 480 px", max(thumb.size) <= 480, True)
            check("much smaller than the original", len(r.content) < len(original) / 4, True)

            print("\n5. The report PDF carries it")
            r = await c.get(f"{BASE}/babies/{baby_id}/report/pdf", headers=P)
            check("pdf generated", r.status_code, 200)
            text = pdf_text(r.content)
            check("has the photo section", b"Dokumentasi Foto" in text, True)
            n_photos = await conn.fetchval(
                "SELECT count(*) FROM monitoring_records WHERE baby_id = $1 AND foto_url IS NOT NULL", uuid.UUID(baby_id))
            check("says how many photos", f"{n_photos} foto dari".encode() in text, True)
            check("embeds JPEG images", r.content.count(b"/DCTDecode") >= n_photos, True)
            # Re-encoded, not pasted in whole: one untouched 1400 px photo alone is
            # bigger than the entire report should be.
            check("stays small", len(r.content) < 1_500_000, True)
            print(f"      ({n_photos} photo(s), pdf {len(r.content) / 1000:.0f} KB, "
                  f"original alone {len(original) / 1000:.0f} KB)")

            print("\n6. A record whose file has vanished does not break the report")
            path = await conn.fetchval(
                "SELECT foto_url FROM monitoring_records WHERE monitoring_id = $1", uuid.UUID(monitoring_id))
            await conn.execute(
                "UPDATE monitoring_records SET foto_url = '/uploads/nope/missing.jpg' WHERE monitoring_id = $1",
                uuid.UUID(monitoring_id))
            check("report still renders",
                  (await c.get(f"{BASE}/babies/{baby_id}/report/pdf", headers=P)).status_code, 200)
            check("photo endpoint 404s",
                  (await c.get(f"{BASE}/monitoring/{monitoring_id}/photo", headers=P)).status_code, 404)
            await conn.execute(
                "UPDATE monitoring_records SET foto_url = $2 WHERE monitoring_id = $1",
                uuid.UUID(monitoring_id), path)

            print("\n7. A path that tries to climb out of the uploads directory is refused")
            await conn.execute(
                "UPDATE monitoring_records SET foto_url = '/uploads/../../.env' WHERE monitoring_id = $1",
                uuid.UUID(monitoring_id))
            check("no traversal",
                  (await c.get(f"{BASE}/monitoring/{monitoring_id}/photo", headers=A)).status_code, 404)
            await conn.execute(
                "UPDATE monitoring_records SET foto_url = $2 WHERE monitoring_id = $1",
                uuid.UUID(monitoring_id), path)
    finally:
        if monitoring_id:
            row = await conn.fetchrow(
                "DELETE FROM monitoring_records WHERE monitoring_id = $1 RETURNING foto_url, baby_id",
                uuid.UUID(monitoring_id))
            if row and row["foto_url"]:
                import pathlib

                from app.core.config import settings  # noqa: E402

                p = pathlib.Path(settings.storage_local_path) / row["foto_url"][len("/uploads/"):]
                p.unlink(missing_ok=True)
        await conn.close()

    passed = sum(1 for ok, _ in results if ok)
    print(f"\n{passed}/{len(results)} passed")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    asyncio.run(main())
