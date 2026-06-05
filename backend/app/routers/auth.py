from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.config import settings
from app.limiter import limiter
from app.models.user import User, RoleEnum
from app.models.etudiant import Etudiant
from app.models.entreprise import Entreprise
from app.schemas.user import (
    RegisterRequest, LoginRequest, TokenResponse,
    RefreshRequest, AccessTokenResponse,
    ForgotPasswordRequest, ResetPasswordRequest,
)
from app.services.auth_service import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
)
from app.services.token_service import (
    generate_password_reset_token, verify_password_reset_token,
)
from app.services.email_service import send_password_reset_email
from app.middleware.auth_middleware import get_current_user
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests


import re


def validate_strong_password(pwd: str):
    """Vérifie qu'un mot de passe est fort. Lève HTTPException sinon."""
    errors = []
    if len(pwd) < 8:
        errors.append("au moins 8 caractères")
    if not re.search(r"[A-Z]", pwd):
        errors.append("une lettre majuscule")
    if not re.search(r"[a-z]", pwd):
        errors.append("une lettre minuscule")
    if not re.search(r"\d", pwd):
        errors.append("un chiffre")
    if not re.search(r"[^A-Za-z0-9]", pwd):
        errors.append("un caractère spécial (!@#$...)")
    if errors:
        raise HTTPException(
            status_code=400,
            detail="Le mot de passe doit contenir : " + ", ".join(errors) + ".",
        )


class ChangePasswordRequest(BaseModel):
    ancien_mot_de_passe: str
    nouveau_mot_de_passe: str


class GoogleAuthRequest(BaseModel):
    credential: str

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/hour")
def register(request: Request, body: RegisterRequest, db: Session = Depends(get_db)):
    validate_strong_password(body.password)

    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email déjà utilisé")

    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        role=body.role,
    )
    db.add(user)
    db.flush()

    if body.role == RoleEnum.etudiant:
        etudiant = Etudiant(id=user.id, nom="", prenom="")
        db.add(etudiant)
    elif body.role == RoleEnum.entreprise:
        entreprise = Entreprise(id=user.id, nom_entreprise="")
        db.add(entreprise)
        from app.services.notification_service import notify_all_club
        notify_all_club(
            db,
            "Nouvelle entreprise inscrite",
            f"Une nouvelle entreprise ({body.email}) vient de créer un compte et attend validation.",
        )

    db.commit()
    return {"message": "Compte créé avec succès"}


@router.post("/google", response_model=TokenResponse)
@limiter.limit("10/minute")
def google_login(request: Request, body: GoogleAuthRequest, db: Session = Depends(get_db)):
    """Authentification via Google — réservée aux étudiants @enim.ac.ma."""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google OAuth non configuré")

    try:
        idinfo = google_id_token.verify_oauth2_token(
            body.credential, google_requests.Request(), settings.GOOGLE_CLIENT_ID
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="Token Google invalide")

    email = idinfo.get("email", "").lower().strip()
    if not email.endswith("@enim.ac.ma"):
        raise HTTPException(
            status_code=403,
            detail="Seuls les comptes @enim.ac.ma sont autorisés à se connecter avec Google.",
        )

    user = db.query(User).filter(func.lower(User.email) == email).first()

    if not user:
        # Créer automatiquement le compte étudiant
        user = User(
            email=email,
            password_hash=hash_password(uuid4().hex),  # mot de passe aléatoire
            role=RoleEnum.etudiant,
        )
        db.add(user)
        db.flush()

        prenom = idinfo.get("given_name", "")
        nom = idinfo.get("family_name", "")
        etudiant = Etudiant(id=user.id, nom=nom, prenom=prenom)
        db.add(etudiant)
        db.commit()
    elif not user.is_active:
        raise HTTPException(status_code=403, detail="Compte désactivé")

    token_data = {"sub": str(user.id), "role": user.role, "mcp": False}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
def login(request: Request, body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(func.lower(User.email) == body.email.strip().lower()).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Compte désactivé")

    token_data = {"sub": str(user.id), "role": user.role, "mcp": user.must_change_password}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    payload = decode_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Refresh token invalide")

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Utilisateur introuvable")

    token_data = {"sub": str(user.id), "role": user.role, "mcp": user.must_change_password}
    return AccessTokenResponse(access_token=create_access_token(token_data))


@router.post("/forgot-password")
@limiter.limit("3/hour")
def forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Envoie un lien de réinitialisation si un compte actif existe pour cette adresse.
    Renvoie toujours la même réponse générique pour ne pas révéler l'existence d'un compte.
    L'envoi se fait en arrière-plan (timing constant, pas de fuite par latence).
    """
    user = db.query(User).filter(func.lower(User.email) == body.email.strip().lower()).first()
    if user and user.is_active:
        token = generate_password_reset_token(str(user.id))
        reset_link = f"{settings.FRONTEND_URL}/reset-password?token={token}"
        background_tasks.add_task(send_password_reset_email, user.email, reset_link)

    return {
        "message": "Si un compte est associé à cette adresse, un email de "
                   "réinitialisation vient d'être envoyé."
    }


@router.post("/reset-password")
@limiter.limit("5/hour")
def reset_password(
    request: Request,
    body: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    user_id = verify_password_reset_token(body.token)
    if not user_id:
        raise HTTPException(
            status_code=400,
            detail="Lien invalide ou expiré. Veuillez refaire une demande de réinitialisation.",
        )
    validate_strong_password(body.nouveau_mot_de_passe)

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=400,
            detail="Lien invalide ou expiré. Veuillez refaire une demande de réinitialisation.",
        )

    user.password_hash = hash_password(body.nouveau_mot_de_passe)
    user.must_change_password = False
    db.commit()
    return {"message": "Mot de passe réinitialisé avec succès. Vous pouvez maintenant vous connecter."}


@router.post("/logout")
def logout():
    # Stateless JWT — client just discards tokens
    return {"message": "Déconnecté"}


class ForceChangePasswordRequest(BaseModel):
    nouveau_mot_de_passe: str


@router.put("/force-change-password")
def force_change_password(
    body: ForceChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Changement obligatoire lors de la première connexion."""
    if not current_user.must_change_password:
        raise HTTPException(status_code=400, detail="Aucun changement de mot de passe requis")
    validate_strong_password(body.nouveau_mot_de_passe)
    current_user.password_hash = hash_password(body.nouveau_mot_de_passe)
    current_user.must_change_password = False
    db.commit()
    # Renvoyer de nouveaux tokens sans le flag mcp
    token_data = {"sub": str(current_user.id), "role": current_user.role, "mcp": False}
    return {
        "message": "Mot de passe modifié avec succès",
        "access_token": create_access_token(token_data),
        "refresh_token": create_refresh_token(token_data),
    }


@router.put("/change-password")
def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(body.ancien_mot_de_passe, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Mot de passe actuel incorrect")
    validate_strong_password(body.nouveau_mot_de_passe)
    current_user.password_hash = hash_password(body.nouveau_mot_de_passe)
    current_user.must_change_password = False
    db.commit()
    return {"message": "Mot de passe modifié avec succès"}
