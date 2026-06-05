import os
import uuid
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, Request
from fastapi.responses import FileResponse, RedirectResponse, Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, RoleEnum
from app.models.etudiant import Etudiant
from app.models.cv import CV
from app.models.candidature import Candidature
from app.models.annonce import Annonce
from app.models.entreprise import Entreprise
from app.schemas.etudiant import EtudiantUpdate, EtudiantOut, CVOut
from app.schemas.candidature import CandidatureOut
from app.middleware.auth_middleware import get_current_etudiant, get_current_user
from app.tasks.analyze_cv import analyze_cv_background
from app.services import storage_service
from app.config import settings
from app.limiter import limiter

router = APIRouter(prefix="/etudiants", tags=["Étudiants"])

MAX_CV_SIZE = 10 * 1024 * 1024  # 10 Mo


@router.get("/me", response_model=EtudiantOut)
def get_my_profile(
    current_user: User = Depends(get_current_etudiant),
    db: Session = Depends(get_db),
):
    etudiant = db.query(Etudiant).filter(Etudiant.id == current_user.id).first()
    if not etudiant:
        raise HTTPException(status_code=404, detail="Profil introuvable")
    data = EtudiantOut.model_validate(etudiant)
    data.email = current_user.email
    return data


@router.put("/me", response_model=EtudiantOut)
def update_my_profile(
    body: EtudiantUpdate,
    current_user: User = Depends(get_current_etudiant),
    db: Session = Depends(get_db),
):
    etudiant = db.query(Etudiant).filter(Etudiant.id == current_user.id).first()
    if not etudiant:
        raise HTTPException(status_code=404, detail="Profil introuvable")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(etudiant, field, value)
    db.commit()
    db.refresh(etudiant)
    data = EtudiantOut.model_validate(etudiant)
    data.email = current_user.email
    return data


@router.post("/me/photo")
def upload_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_etudiant),
    db: Session = Depends(get_db),
):
    allowed = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail="Format d'image non supporté (jpeg, png, webp)")

    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "jpg"
    contents = file.file.read()

    photo_url = storage_service.save_photo(str(current_user.id), contents, ext)

    etudiant = db.query(Etudiant).filter(Etudiant.id == current_user.id).first()
    etudiant.photo_url = photo_url
    db.commit()

    return {"photo_url": etudiant.photo_url}


@router.delete("/me/photo")
def delete_photo(
    current_user: User = Depends(get_current_etudiant),
    db: Session = Depends(get_db),
):
    etudiant = db.query(Etudiant).filter(Etudiant.id == current_user.id).first()
    if not etudiant or not etudiant.photo_url:
        raise HTTPException(status_code=404, detail="Aucune photo à supprimer")
    storage_service.delete_photo(str(current_user.id))
    etudiant.photo_url = None
    db.commit()
    return {"ok": True}


@router.post("/me/cv")
@limiter.limit("3/hour")
def upload_cv(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    consentement_ia: bool = Form(True),
    current_user: User = Depends(get_current_etudiant),
    db: Session = Depends(get_db),
):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Seuls les fichiers PDF sont acceptés")

    if not consentement_ia:
        raise HTTPException(
            status_code=400,
            detail="L'analyse IA est requise pour activer le matching. Veuillez accepter le consentement.",
        )

    # Validation renforcée : taille bornée + vérification réelle des octets magiques PDF
    # (le content_type déclaré par le client n'est pas fiable).
    contents = file.file.read(MAX_CV_SIZE + 1)
    if len(contents) > MAX_CV_SIZE:
        raise HTTPException(status_code=413, detail=f"Fichier trop volumineux (max {MAX_CV_SIZE // (1024*1024)} Mo)")
    if not contents.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="Fichier PDF invalide ou corrompu")

    path = storage_service.save_cv(str(current_user.id), contents)

    existing_cv = db.query(CV).filter(CV.etudiant_id == current_user.id).first()
    if existing_cv:
        existing_cv.fichier_url = path
        existing_cv.description_ia = None
        existing_cv.consentement_ia = consentement_ia
        db.commit()
        cv_id = str(existing_cv.id)
    else:
        cv = CV(
            etudiant_id=current_user.id,
            fichier_url=path,
            consentement_ia=consentement_ia,
        )
        db.add(cv)
        db.commit()
        db.refresh(cv)
        cv_id = str(cv.id)

    # AI analysis runs in background only if user consented
    background_tasks.add_task(analyze_cv_background, cv_id)

    return {"message": "CV uploadé. Analyse IA en cours en arrière-plan.", "cv_id": cv_id}


@router.get("/me/cv", response_model=CVOut)
def get_my_cv(
    current_user: User = Depends(get_current_etudiant),
    db: Session = Depends(get_db),
):
    cv = db.query(CV).filter(CV.etudiant_id == current_user.id).first()
    if not cv:
        raise HTTPException(status_code=404, detail="Aucun CV trouvé")
    return CVOut(
        id=str(cv.id),
        fichier_url=f"/api/cv/{current_user.id}",
        description_ia=cv.description_ia,
        uploaded_at=cv.uploaded_at,
        consentement_ia=cv.consentement_ia,
    )


@router.get("/me/candidatures", response_model=list[CandidatureOut])
def get_my_candidatures(
    current_user: User = Depends(get_current_etudiant),
    db: Session = Depends(get_db),
):
    candidatures = (
        db.query(Candidature)
        .filter(Candidature.etudiant_id == current_user.id)
        .all()
    )
    result = []
    for c in candidatures:
        annonce = db.query(Annonce).filter(Annonce.id == c.annonce_id).first()
        entreprise = db.query(Entreprise).filter(Entreprise.id == annonce.entreprise_id).first() if annonce else None
        result.append(
            CandidatureOut(
                id=str(c.id),
                etudiant_id=str(c.etudiant_id),
                annonce_id=str(c.annonce_id),
                date=c.date,
                titre_annonce=annonce.titre if annonce else None,
                nom_entreprise=entreprise.nom_entreprise if entreprise else None,
                logo_url=entreprise.logo_url if entreprise else None,
            )
        )
    return result


cv_router = APIRouter(tags=["CVs"])


@cv_router.get("/api/cv/{etudiant_id}")
def get_cv_file(
    etudiant_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Sert le CV PDF d'un étudiant de façon sécurisée (JWT requis).
    Accessible uniquement par : l'étudiant lui-même, une entreprise validée, ou le club.
    """
    try:
        uid = uuid.UUID(etudiant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID invalide")

    # Contrôle d'accès : on n'autorise pas n'importe quel utilisateur connecté.
    if current_user.role == RoleEnum.club:
        pass
    elif current_user.role == RoleEnum.etudiant:
        if current_user.id != uid:
            raise HTTPException(status_code=403, detail="Accès refusé")
    elif current_user.role == RoleEnum.entreprise:
        entreprise = db.query(Entreprise).filter(Entreprise.id == current_user.id).first()
        if not entreprise or not entreprise.valide:
            raise HTTPException(status_code=403, detail="Accès refusé")
    else:
        raise HTTPException(status_code=403, detail="Accès refusé")

    cv = db.query(CV).filter(CV.etudiant_id == uid).first()
    if not cv:
        raise HTTPException(status_code=404, detail="CV introuvable")

    if not storage_service.cv_exists(etudiant_id):
        raise HTTPException(status_code=404, detail="Fichier CV introuvable")

    # Streaming du PDF à travers le backend (évite les problèmes CORS avec S3).
    if storage_service.is_s3():
        content = storage_service.read_cv(etudiant_id)
        if not content:
            raise HTTPException(status_code=404, detail="Fichier CV introuvable sur S3")
        return Response(
            content=content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="cv_{etudiant_id}.pdf"',
                "X-Content-Type-Options": "nosniff",
            },
        )

    return FileResponse(
        path=storage_service.local_cv_path(etudiant_id),
        media_type="application/pdf",
        filename=f"cv_{etudiant_id}.pdf",
        headers={"X-Content-Type-Options": "nosniff"},
    )
