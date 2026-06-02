"""Background task: extraction structurée + embedding d'une annonce validée."""
import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.annonce import Annonce
from app.models.embedding import Embedding, SourceType
from app.services.embedding_service import generate_embedding
from app.services.ai_service import analyze_annonce_structured, build_annonce_embedding_text


def embed_annonce_background(annonce_id: str) -> None:
    db: Session = SessionLocal()
    try:
        annonce = db.query(Annonce).filter(Annonce.id == uuid.UUID(annonce_id)).first()
        if not annonce:
            return

        donnees = analyze_annonce_structured(annonce.titre, annonce.description)
        annonce.donnees_ia = donnees or None
        db.add(annonce)
        db.flush()

        text = build_annonce_embedding_text(annonce.titre, annonce.description, donnees)
        vector = generate_embedding(text)

        existing = (
            db.query(Embedding)
            .filter(
                Embedding.source_type == SourceType.annonce,
                Embedding.source_id == annonce.id,
            )
            .first()
        )
        if existing:
            existing.vecteur = vector
            existing.updated_at = datetime.utcnow()
            db.add(existing)
        else:
            emb = Embedding(
                source_type=SourceType.annonce,
                source_id=annonce.id,
                vecteur=vector,
            )
            db.add(emb)

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
