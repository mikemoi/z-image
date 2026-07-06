"""Filesystem helpers for uploaded images.

The database keeps metadata, but the canonical disk location is derived from
FILES_ROOT + checksum so a database moved between local/Docker environments
does not strand old images behind stale absolute paths.
"""
from pathlib import Path

from fastapi import HTTPException, UploadFile

from config import FILES_ROOT, UPLOAD_ALLOWED_EXTENSIONS, UPLOAD_MAX_BYTES

IMAGE_DIR = Path(FILES_ROOT) / "image"


def ext_from_name(name: str) -> str:
    ext = Path(name or "").suffix.lower().lstrip(".")
    ext = "".join(c for c in ext if c.isalnum())
    return ext or "jpg"


def validate_upload_meta(up: UploadFile) -> str:
    ext = ext_from_name(up.filename or "")
    if ext not in UPLOAD_ALLOWED_EXTENSIONS:
        raise HTTPException(415, f"unsupported image type: .{ext}")
    return ext


async def read_limited_upload(up: UploadFile) -> bytes:
    data = await up.read(UPLOAD_MAX_BYTES + 1)
    if len(data) > UPLOAD_MAX_BYTES:
        raise HTTPException(413, f"image too large; max {UPLOAD_MAX_BYTES} bytes")
    return data


def path_for_checksum(checksum: str, ext: str) -> Path:
    return IMAGE_DIR / f"{checksum}.{ext}"


def path_from_record(checksum: str, db_path: str | None = None, original_filename: str | None = None) -> Path:
    suffix = Path(db_path or "").suffix.lower()
    if not suffix:
        suffix = "." + ext_from_name(original_filename or "")
    canonical = IMAGE_DIR / f"{checksum}{suffix}"
    if canonical.exists():
        return canonical
    legacy = Path(db_path or "")
    if legacy.exists():
        return legacy
    return canonical
