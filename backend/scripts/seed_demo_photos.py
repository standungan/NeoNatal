"""Attach sample photos to seeded monitoring records, so a demo has something to show.

    backend/venv/Scripts/python scripts/seed_demo_photos.py            # 3 per baby
    backend/venv/Scripts/python scripts/seed_demo_photos.py --all      # every record
    backend/venv/Scripts/python scripts/seed_demo_photos.py --clear    # remove them again

    docker compose exec backend python scripts/seed_demo_photos.py     # on a deployment

The images are DRAWN, not photographs: an illustrated incubator scene, watermarked
"CONTOH", carrying the baby's name and the observation time. Demo data must never be
mistaken for a real patient photo, and a stock photo of someone's baby has no place in
a clinical system either.

Files land in the same place uploads do (STORAGE_LOCAL_PATH, a volume under Docker),
and `monitoring_records.foto_url` is pointed at them, exactly as an upload would. Only
records that have no photo are touched, unless --force. Nothing is written to the audit
log: this is seeding, not something a person did.
"""
import argparse
import asyncio
import math
import os
import pathlib
import random
import sys
from datetime import datetime

BACKEND = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)

from dotenv import load_dotenv  # noqa: E402

load_dotenv(".env")

from PIL import Image, ImageDraw, ImageFont  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import AsyncSessionLocal  # noqa: E402
from app.models.baby import Baby  # noqa: E402
from app.models.monitoring import MonitoringRecord  # noqa: E402

W, H = 1200, 900
SKIN = [(247, 219, 195), (236, 200, 173), (222, 183, 152)]
BLANKET = [(255, 214, 222), (214, 231, 255), (226, 240, 224), (255, 236, 214), (231, 222, 245)]
HAT = [(244, 160, 178), (140, 178, 232), (150, 197, 156), (240, 190, 120), (176, 156, 220)]
FONTS = [
    "C:/Windows/Fonts/segoeui.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]


def font(size: int):
    for path in FONTS:
        if pathlib.Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                pass
    return ImageFont.load_default(size=size)


def _gradient(draw, top, bottom):
    for y in range(H):
        t = y / H
        draw.line([(0, y), (W, y)],
                  fill=tuple(round(a + (b - a) * t) for a, b in zip(top, bottom)))


def render(baby_name: str, when: datetime, seed: int) -> Image.Image:
    """One illustrated incubator scene. `seed` keeps each record's image its own."""
    rnd = random.Random(seed)
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    _gradient(d, (240, 245, 251), (208, 221, 238))

    blanket = BLANKET[rnd.randrange(len(BLANKET))]
    hat = HAT[rnd.randrange(len(HAT))]
    skin = SKIN[rnd.randrange(len(SKIN))]
    head_left = rnd.random() < 0.5

    # trolley + base unit the hood sits on
    d.ellipse([150, 770, 1050, 830], fill=(196, 209, 226))          # soft shadow
    d.rounded_rectangle([200, 700, 1000, 790], 18, fill=(228, 236, 246), outline=(176, 193, 214), width=3)
    for cx in (300, 900):                                            # knobs
        d.ellipse([cx - 16, 726, cx + 16, 758], fill=(206, 218, 233), outline=(176, 193, 214), width=2)

    # acrylic hood
    d.rounded_rectangle([210, 250, 990, 706], 46, fill=(249, 252, 255), outline=(168, 190, 216), width=5)
    d.rounded_rectangle([238, 276, 962, 680], 34, outline=(226, 235, 246), width=3)
    d.polygon([(268, 292), (430, 292), (300, 664), (268, 664)], fill=(255, 255, 255))   # glass highlight

    # mattress, with the baby resting ON it — everything below is positioned from
    # its centre line so the scene stays centred whichever way the baby faces.
    mattress = [290, 496, 910, 672]
    d.rounded_rectangle(mattress, 26, fill=(238, 242, 249), outline=(214, 226, 240), width=3)
    cx, cy = 600, 572

    # swaddle
    bx0, bx1, by0, by1 = cx - 200, cx + 200, cy - 66, cy + 64
    d.rounded_rectangle([bx0, by0, bx1, by1], 58, fill=blanket,
                        outline=tuple(max(0, c - 28) for c in blanket), width=3)
    for i in range(4):                                               # blanket folds
        fx = bx0 + 70 + i * ((bx1 - bx0 - 140) / 3)
        d.line([(fx + 12, by0 + 22), (fx - 8, by1 - 20)],
               fill=tuple(max(0, c - 22) for c in blanket), width=4)

    # head, tucked against whichever end the baby lies on
    hx = (bx0 - 56) if head_left else (bx1 + 56)
    d.ellipse([hx - 62, cy - 62, hx + 62, cy + 62], fill=skin)
    d.chord([hx - 66, cy - 72, hx + 66, cy + 56], 180, 360, fill=hat)
    d.arc([hx - 68, cy - 26, hx + 68, cy + 14], 200, 340,
          fill=tuple(max(0, c - 30) for c in hat), width=5)
    for ex in (hx - 24, hx + 24):                                    # closed, sleeping
        d.arc([ex - 14, cy - 12, ex + 14, cy + 8], 200, 340, fill=(120, 96, 84), width=4)
    d.arc([hx - 13, cy + 16, hx + 13, cy + 38], 20, 160, fill=(190, 130, 120), width=4)

    # Sensor lead from the swaddle to a probe on the wall AWAY from the head — on
    # the head's own side it runs behind it and cannot be seen.
    wall = 950 if head_left else 250
    x0 = bx1 if head_left else bx0
    pts = [(x0 + (wall - x0) * t / 6, cy + 22 + 18 * math.sin(t * 1.1)) for t in range(7)]
    d.line(pts, fill=(140, 160, 186), width=5, joint="curve")
    d.rounded_rectangle([wall - 28, cy + 4, wall + 28, cy + 50], 8,
                        fill=(238, 243, 250), outline=(168, 190, 216), width=3)
    d.ellipse([wall - 8, cy + 19, wall + 8, cy + 35], fill=(96, 186, 128))

    # captions
    f_name, f_meta, f_tag = font(40), font(30), font(26)
    d.rounded_rectangle([60, 60, 60 + int(d.textlength("CONTOH - DATA DEMO", f_tag)) + 40, 116],
                        26, fill=(253, 240, 214), outline=(226, 186, 110), width=3)
    d.text((80, 74), "CONTOH - DATA DEMO", font=f_tag, fill=(150, 108, 22))
    d.text((60, 800), baby_name, font=f_name, fill=(34, 48, 66))
    d.text((60, 848), when.strftime("%d %b %Y  %H:%M"), font=f_meta, fill=(96, 112, 132))
    d.text((W - 60 - d.textlength("Neonatal Care System", f_meta), 848),
           "Neonatal Care System", font=f_meta, fill=(128, 146, 168))
    return img


async def main(per_baby: int, every: bool, force: bool, clear: bool) -> None:
    root = pathlib.Path(settings.storage_local_path)
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(
            select(MonitoringRecord, Baby.baby_name)
            .join(Baby, Baby.baby_id == MonitoringRecord.baby_id)
            .order_by(MonitoringRecord.baby_id, MonitoringRecord.observation_time.desc())
        )).all()

        if clear:
            removed = 0
            for rec, _ in rows:
                if rec.foto_url:
                    path = root / rec.foto_url[len("/uploads/"):]
                    path.unlink(missing_ok=True)
                    rec.foto_url = None
                    removed += 1
            await db.commit()
            print(f"  cleared {removed} photos")
            return

        per: dict = {}
        written = 0
        for rec, baby_name in rows:
            if rec.foto_url and not force:
                continue
            n = per.get(rec.baby_id, 0)
            if not every and n >= per_baby:
                continue
            per[rec.baby_id] = n + 1

            rel = f"{rec.baby_id}/{rec.monitoring_id}.jpg"
            dest = root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            render(baby_name, rec.observation_time, seed=rec.monitoring_id.int).save(
                dest, "JPEG", quality=82, optimize=True)
            rec.foto_url = f"/uploads/{rel}"
            written += 1
        await db.commit()
    size = sum(p.stat().st_size for p in root.rglob("*.jpg")) / 1e6
    print(f"  wrote {written} sample photos for {len(per)} babies into {root} ({size:.1f} MB total)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--per-baby", type=int, default=3, help="how many per baby (default 3)")
    ap.add_argument("--all", action="store_true", help="every monitoring record, not just a few")
    ap.add_argument("--force", action="store_true", help="replace photos that are already there")
    ap.add_argument("--clear", action="store_true", help="delete the photos and clear foto_url")
    a = ap.parse_args()
    asyncio.run(main(a.per_baby, a.all, a.force, a.clear))
