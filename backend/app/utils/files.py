import mimetypes
import uuid
from pathlib import Path

from fastapi import UploadFile

from ..config import settings

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def _safe_extension(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    return ext if ext in ALLOWED_EXTENSIONS else ".jpg"


def _get_r2_client():
    import boto3
    from botocore.client import Config as BotoConfig

    return boto3.client(
        "s3",
        endpoint_url=f"https://{settings.r2_account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        config=BotoConfig(signature_version="s3v4"),
        region_name="auto",
    )


def _save_to_r2(data: bytes, key: str) -> str:
    client = _get_r2_client()
    content_type = mimetypes.guess_type(key)[0] or "application/octet-stream"
    client.put_object(Bucket=settings.r2_bucket_name, Key=key, Body=data, ContentType=content_type)
    return f"{settings.r2_public_url.rstrip('/')}/{key}"


def _save_to_disk(data: bytes, subfolder: str, filename: str) -> str:
    target_dir = Path(settings.upload_dir) / subfolder
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / filename).write_bytes(data)
    return f"{subfolder}/{filename}"


def save_upload(file: UploadFile, subfolder: str) -> str:
    """Saves an uploaded file and returns a value that [deps.absolute_url]
    knows how to resolve:
    - If Cloudflare R2 is configured, this is the object's full public URL.
    - Otherwise, it's a path relative to UPLOAD_DIR (e.g. 'avatars/ab12.jpg'),
      served locally by the app's own /uploads static mount.
    """
    filename = f"{uuid.uuid4().hex}{_safe_extension(file.filename or '')}"
    data = file.file.read()
    file.file.close()

    if settings.r2_configured:
        return _save_to_r2(data, f"{subfolder}/{filename}")
    return _save_to_disk(data, subfolder, filename)


def delete_upload(stored_value: str | None) -> None:
    if not stored_value:
        return

    if stored_value.startswith("http://") or stored_value.startswith("https://"):
        if not settings.r2_configured:
            return
        prefix = settings.r2_public_url.rstrip("/") + "/"
        if not stored_value.startswith(prefix):
            return
        key = stored_value[len(prefix):]
        try:
            _get_r2_client().delete_object(Bucket=settings.r2_bucket_name, Key=key)
        except Exception:
            pass  # best-effort cleanup — a failed delete shouldn't break the request
        return

    path = Path(settings.upload_dir) / stored_value
    if path.exists():
        path.unlink(missing_ok=True)
