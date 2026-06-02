"""Background task: extract text → extraction structurée IA → embedding → DB.

Le résumé lisible (prose) est stocké dans description_ia, les champs structurés
dans donnees_ia, et l'embedding est construit sur un texte canonique enrichi.
Détecte les PDF non lisibles (scannés) et notifie l'étudiant au lieu d'échouer
en silence."""
import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.cv import CV
from app.models.embedding import Embedding, SourceType
from app.services.cv_service import extract_text_from_pdf_bytes
from app.services.embedding_service import generate_embedding
from app.services.ai_service import analyze_cv_structured, build_cv_embedding_text
from app.services.notification_service import create_notification
from app.services import storage_service

# Seuil en dessous duquel on considère le PDF comme non exploitable (probablement scanné)
_MIN_TEXT_LEN = 40


def analyze_cv_background(cv_id: str) -> None:
    db: Session = SessionLocal()
    try:
        cv = db.query(CV).filter(CV.id == uuid.UUID(cv_id)).first()
        if not cv:
            return

        # Pas de consentement → on ne fait aucun appel OpenAI
        if not cv.consentement_ia:
            return

        data = storage_service.read_cv(str(cv.etudiant_id))
        text = extract_text_from_pdf_bytes(data) if data else ""
        if not text or len(text.strip()) < _MIN_TEXT_LEN:
            # PDF probablement scanné / image : aucun texte exploitable
            create_notification(
                db,
                cv.etudiant_id,
                "CV non analysable",
                "Nous n'avons pas pu lire le texte de votre CV (PDF scanné ou image ?). "
                "Merci de renvoyer un CV au format PDF texte pour activer le matching.",
            )
            db.commit()
            return

        donnees = analyze_cv_structured(text)
        cv.description_ia = donnees.get("resume") or None
        cv.donnees_ia = donnees or None
        db.add(cv)
        db.flush()

        embedding_text = build_cv_embedding_text(donnees, fallback_text=text)
        vector = generate_embedding(embedding_text)

        existing = (
            db.query(Embedding)
            .filter(
                Embedding.source_type == SourceType.cv,
                Embedding.source_id == cv.id,
            )
            .first()
        )
        if existing:
            existing.vecteur = vector
            existing.updated_at = datetime.utcnow()
            db.add(existing)
        else:
            db.add(Embedding(source_type=SourceType.cv, source_id=cv.id, vecteur=vector))

        create_notification(
            db,
            cv.etudiant_id,
            "CV analysé par l'IA",
            "Votre CV a été analysé avec succès. Votre profil est maintenant optimisé pour le matching avec les offres.",
        )

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
