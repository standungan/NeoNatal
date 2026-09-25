import uuid
from io import BytesIO
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from PIL import Image

from app.core.config import settings

ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp"}
MAX_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB

CONTENT_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
                 ".webp": "image/webp"}


async def save_photo(file: UploadFile, baby_id: uuid.UUID, monitoring_id: uuid.UUID) -> str:
    if file.content_type not in ALLOWED_MIME:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Format file harus JPEG, PNG, atau WebP",
        )

    contents = await file.read()
    if len(contents) > MAX_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Ukuran file maksimal 5 MB",
        )

    ext = Path(file.filename).suffix.lower() if file.filename else ".jpg"
    relative_path = f"{baby_id}/{monitoring_id}{ext}"

    if settings.storage_backend == "local":
        return await _save_local(contents, relative_path)

    # S3 path (to be wired when STORAGE_BACKEND=s3)
    raise HTTPException(status_code=500, detail="S3 storage not configured")


async def _save_local(contents: bytes, relative_path: str) -> str:
    dest = Path(settings.storage_local_path) / relative_path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(contents)
    return f"/uploads/{relative_path}"


def photo_path(foto_url: str | None) -> Path | None:
    """The stored file behind a `foto_url`, or None if it is not readable.

    `foto_url` comes from our own column, but it is still joined onto a base
    directory here, so the result is checked to be inside that directory: a
    stray "../" in the database must not turn into a file read anywhere on disk.

    Returns None rather than raising — a report whose photo file has gone
    missing should print without it, not fail.
    """
    if not foto_url or not foto_url.startswith("/uploads/"):
        return None
    root = Path(settings.storage_local_path).resolve()
    candidate = (root / foto_url[len("/uploads/"):]).resolve()
    if root not in candidate.parents or not candidate.is_file():
        return None
    return candidate


def content_type_for(path: Path) -> str:
    return CONTENT_TYPES.get(path.suffix.lower(), "application/octet-stream")


def resized_jpeg(path: Path, max_px: int, quality: int = 72) -> bytes | None:
    """The photo as a JPEG no wider or taller than `max_px`, or None if unreadable.

    Used for both the on-screen thumbnail and the copy embedded in the PDF: the
    original may be 5 MB, and a report with every monitoring photo at that size
    would be unusable. The stored file is never modified.

    Transparency is flattened onto white — JPEG has no alpha, and a PNG with a
    transparent background would otherwise come out with a black one.
    """
    try:
        with Image.open(path) as img:
            img = img.convert("RGBA") if img.mode in ("P", "LA", "RGBA") else img.convert("RGB")
            if img.mode == "RGBA":
                flat = Image.new("RGB", img.size, (255, 255, 255))
                flat.paste(img, mask=img.split()[3])
                img = flat
            img.thumbnail((max_px, max_px), Image.LANCZOS)
            out = BytesIO()
            img.save(out, format="JPEG", quality=quality, optimize=True)
            return out.getvalue()
    except (OSError, ValueError):
        return None
