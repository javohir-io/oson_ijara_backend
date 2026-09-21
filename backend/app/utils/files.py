import uuid
from pathlib import Path

from fastapi import UploadFile

from ..config import settings

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def _safe_extension(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    return ext if ext in ALLOWED_EXTENSIONS else ".jpg"


def save_upload(file: UploadFile, subfolder: str) -> str:
    """Saves an uploaded file under UPLOAD_DIR/subfolder/<uuid>.<ext> and
    returns the path relative to UPLOAD_DIR (e.g. 'avatars/ab12.jpg')."""
    upload_root = Path(settings.upload_dir)
    target_dir = upload_root / subfolder
    target_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid.uuid4().hex}{_safe_extension(file.filename or '')}"
    destination = target_dir / filename

    with destination.open("wb") as buffer:
        while chunk := file.file.read(1024 * 1024):
            buffer.write(chunk)
    file.file.close()

    return f"{subfolder}/{filename}"


def delete_upload(relative_path: str | None) -> None:
    if not relative_path:
        return
    path = Path(settings.upload_dir) / relative_path
    if path.exists():
        path.unlink(missing_ok=True)
