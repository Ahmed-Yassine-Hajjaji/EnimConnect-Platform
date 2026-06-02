"""HMAC-SHA256 signed tokens for email validation links (48h expiry)."""
import hmac
import hashlib
import time
from typing import Optional
from app.config import settings

EXPIRY_SECONDS = 48 * 3600
RESET_EXPIRY_SECONDS = 3600  # Liens de réinitialisation de mot de passe : 1h


def _sign(payload: str) -> str:
    return hmac.new(
        settings.HMAC_SECRET.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()


# ── Legacy tokens (annonce-level) ──────────────────────────────────────────────

def generate_validation_token(annonce_id: str, chef_id: str) -> str:
    ts = int(time.time())
    payload = f"{annonce_id}:{chef_id}:{ts}"
    sig = _sign(payload)
    return f"{ts}:{sig}"


def verify_validation_token(token: str, annonce_id: str, chef_id: str) -> bool:
    try:
        ts_str, sig = token.split(":", 1)
        ts = int(ts_str)
    except ValueError:
        return False
    if time.time() - ts > EXPIRY_SECONDS:
        return False
    payload = f"{annonce_id}:{chef_id}:{ts}"
    expected = _sign(payload)
    return hmac.compare_digest(expected, sig)


# ── Per-department validation tokens ───────────────────────────────────────────

def generate_validation_token_dept(validation_dept_id: str, chef_id: str) -> str:
    """Token HMAC pour valider/rejeter une offre pour un département précis."""
    ts = int(time.time())
    payload = f"dept:{validation_dept_id}:{chef_id}:{ts}"
    sig = _sign(payload)
    return f"{ts}:{sig}"


def verify_validation_token_dept(token: str, validation_dept_id: str, chef_id: str) -> bool:
    try:
        ts_str, sig = token.split(":", 1)
        ts = int(ts_str)
    except ValueError:
        return False
    if time.time() - ts > EXPIRY_SECONDS:
        return False
    payload = f"dept:{validation_dept_id}:{chef_id}:{ts}"
    expected = _sign(payload)
    return hmac.compare_digest(expected, sig)


# ── Tokens de réinitialisation de mot de passe ─────────────────────────────────

def generate_password_reset_token(user_id: str) -> str:
    """Token HMAC signé contenant l'id utilisateur (expiration 1h)."""
    ts = int(time.time())
    payload = f"reset:{user_id}:{ts}"
    sig = _sign(payload)
    return f"{user_id}:{ts}:{sig}"


def verify_password_reset_token(token: str) -> Optional[str]:
    """Retourne l'user_id si le token est valide et non expiré, sinon None."""
    try:
        user_id, ts_str, sig = token.split(":")
        ts = int(ts_str)
    except ValueError:
        return None
    if time.time() - ts > RESET_EXPIRY_SECONDS:
        return None
    expected = _sign(f"reset:{user_id}:{ts}")
    if not hmac.compare_digest(expected, sig):
        return None
    return user_id
