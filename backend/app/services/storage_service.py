"""Abstraction du stockage des CV : disque local ou Amazon S3.

Le backend est choisi par settings.STORAGE_BACKEND ("local" | "s3"). Les CV sont
toujours rangés sous la clé déterministe ``cvs/{etudiant_id}.pdf``, ce qui rend le
service indépendant de la valeur de cv.fichier_url."""
import os
from typing import Optional
from app.config import settings


def is_s3() -> bool:
    return settings.STORAGE_BACKEND.lower() == "s3"


def _cv_key(etudiant_id: str) -> str:
    return f"cvs/{etudiant_id}.pdf"


def local_cv_path(etudiant_id: str) -> str:
    return os.path.join(settings.STORAGE_PATH, "cvs", f"{etudiant_id}.pdf")


_s3_client = None


def _s3():
    global _s3_client
    if _s3_client is None:
        import boto3
        from botocore.config import Config
        kwargs = {
            "region_name": settings.AWS_REGION,
            # Endpoint régional explicite + SigV4 → évite le redirect 307 du
            # endpoint global et les erreurs de signature sur eu-north-1.
            "endpoint_url": f"https://s3.{settings.AWS_REGION}.amazonaws.com",
            "config": Config(signature_version="s3v4", s3={"addressing_style": "virtual"}),
        }
        if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
            kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
            kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY
        _s3_client = boto3.client("s3", **kwargs)
    return _s3_client


def save_cv(etudiant_id: str, content: bytes) -> str:
    """Enregistre le PDF et renvoie la référence à stocker dans cv.fichier_url."""
    if is_s3():
        _s3().put_object(
            Bucket=settings.S3_BUCKET,
            Key=_cv_key(etudiant_id),
            Body=content,
            ContentType="application/pdf",
        )
        return f"s3://{settings.S3_BUCKET}/{_cv_key(etudiant_id)}"

    path = local_cv_path(etudiant_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(content)
    return path


def read_cv(etudiant_id: str) -> Optional[bytes]:
    """Lit le contenu du PDF (octets) ou None s'il est absent."""
    if is_s3():
        try:
            obj = _s3().get_object(Bucket=settings.S3_BUCKET, Key=_cv_key(etudiant_id))
            return obj["Body"].read()
        except Exception:
            return None
    path = local_cv_path(etudiant_id)
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return f.read()


def cv_exists(etudiant_id: str) -> bool:
    if is_s3():
        try:
            _s3().head_object(Bucket=settings.S3_BUCKET, Key=_cv_key(etudiant_id))
            return True
        except Exception:
            return False
    return os.path.exists(local_cv_path(etudiant_id))


def cv_presigned_url(etudiant_id: str) -> Optional[str]:
    """URL présignée (S3) pour télécharger le CV ; None en mode local."""
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
