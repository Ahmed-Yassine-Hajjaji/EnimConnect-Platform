"""Abstraction du stockage des fichiers : disque local ou Amazon S3.

Le backend est choisi par settings.STORAGE_BACKEND ("local" | "s3"). Les fichiers sont
rangés sous des clés déterministes :
  - CVs    : cvs/{etudiant_id}.pdf
  - Photos : photos/{user_id}.{ext}
  - Logos  : logos/{entreprise_id}.{ext}
"""
import os
from typing import Optional
from app.config import settings


def is_s3() -> bool:
    return settings.STORAGE_BACKEND.lower() == "s3"


# ── S3 client singleton ─────────────────────────────────────────────────────

_s3_client = None


def _s3():
    global _s3_client
    if _s3_client is None:
        import boto3
        from botocore.config import Config
        kwargs = {
            "region_name": settings.AWS_REGION,
            "endpoint_url": f"https://s3.{settings.AWS_REGION}.amazonaws.com",
            "config": Config(signature_version="s3v4", s3={"addressing_style": "virtual"}),
        }
        if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
            kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
            kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY
        _s3_client = boto3.client("s3", **kwargs)
    return _s3_client


# ── Generic helpers ──────────────────────────────────────────────────────────

def _save_file(key: str, content: bytes, content_type: str) -> str:
    """Save a file to S3 or local disk. Returns the reference to store in DB."""
    if is_s3():
        _s3().put_object(
            Bucket=settings.S3_BUCKET, Key=key, Body=content, ContentType=content_type,
        )
        return f"s3://{settings.S3_BUCKET}/{key}"
    path = os.path.join(settings.STORAGE_PATH, key)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(content)
    return path


def _read_file(key: str) -> Optional[bytes]:
    """Read file content from S3 or local disk."""
    if is_s3():
        try:
            obj = _s3().get_object(Bucket=settings.S3_BUCKET, Key=key)
            return obj["Body"].read()
        except Exception:
            return None
    path = os.path.join(settings.STORAGE_PATH, key)
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return f.read()


# ── CVs ──────────────────────────────────────────────────────────────────────

def _cv_key(etudiant_id: str) -> str:
    return f"cvs/{etudiant_id}.pdf"


def local_cv_path(etudiant_id: str) -> str:
    return os.path.join(settings.STORAGE_PATH, "cvs", f"{etudiant_id}.pdf")


def save_cv(etudiant_id: str, content: bytes) -> str:
    return _save_file(_cv_key(etudiant_id), content, "application/pdf")


def read_cv(etudiant_id: str) -> Optional[bytes]:
    return _read_file(_cv_key(etudiant_id))


def cv_exists(etudiant_id: str) -> bool:
    if is_s3():
        try:
            _s3().head_object(Bucket=settings.S3_BUCKET, Key=_cv_key(etudiant_id))
            return True
        except Exception:
            return False
    return os.path.exists(local_cv_path(etudiant_id))


def cv_presigned_url(etudiant_id: str) -> Optional[str]:
    if not is_s3():
        return None
    return _s3().generate_presigned_url(
        "get_object",
        Params={
            "Bucket": settings.S3_BUCKET,
            "Key": _cv_key(etudiant_id),
            "ResponseContentType": "application/pdf",
            "ResponseContentDisposition": f'attachment; filename="cv_{etudiant_id}.pdf"',
        },
        ExpiresIn=settings.S3_PRESIGN_EXPIRE,
    )


# ── Photos ───────────────────────────────────────────────────────────────────

def save_photo(user_id: str, content: bytes, ext: str = "jpg") -> str:
    key = f"photos/{user_id}.{ext}"
    content_type = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}.get(ext, "image/jpeg")
    _save_file(key, content, content_type)
    return f"/api/photos/{user_id}"


def read_photo(user_id: str) -> Optional[tuple]:
    """Returns (bytes, content_type) or None."""
    for ext in ("jpg", "jpeg", "png", "webp"):
        key = f"photos/{user_id}.{ext}"
        data = _read_file(key)
        if data:
            ct = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}[ext]
            return data, ct
    return None


# ── Logos ────────────────────────────────────────────────────────────────────

def save_logo(entreprise_id: str, content: bytes, ext: str = "jpg") -> str:
    key = f"logos/{entreprise_id}.{ext}"
    content_type = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}.get(ext, "image/jpeg")
    _save_file(key, content, content_type)
    return f"/api/logos/{entreprise_id}"


def read_logo(entreprise_id: str) -> Optional[tuple]:
    """Returns (bytes, content_type) or None."""
    for ext in ("jpg", "jpeg", "png", "webp"):
        key = f"logos/{entreprise_id}.{ext}"
        data = _read_file(key)
        if data:
            ct = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}[ext]
            return data, ct
    return None
