"""Backfill idempotent des données IA (résumés structurés + embeddings).

Ré-analyse les CV et ré-embarque les annonces validées qui n'ont pas encore de
données structurées ou d'embedding. Sans danger à relancer.

Usage (depuis backend/) :
  python scripts/backfill_ai.py            # ne traite que ce qui manque
  python scripts/backfill_ai.py --all      # force le re-traitement de tout
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.cv import CV
from app.models.annonce import Annonce, StatutAnnonce
from app.models.embedding import Embedding, SourceType
from app.tasks.analyze_cv import analyze_cv_background
from app.tasks.embed_annonce import embed_annonce_background


def _has_embedding(db, source_type, source_id) -> bool:
    return (
        db.query(Embedding.id)
        .filter(Embedding.source_type == source_type, Embedding.source_id == source_id)
        .first()
        is not None
    )


def main(force: bool = False) -> None:
    db = SessionLocal()
    cv_done = cv_skip = ann_done = ann_skip = 0
    try:
        for cv in db.query(CV).all():
            if not cv.consentement_ia:
                cv_skip += 1
                continue
            needs = force or cv.donnees_ia is None or not _has_embedding(db, SourceType.cv, cv.id)
            if not needs:
                cv_skip += 1
                continue
            print(f"[CV] analyse {cv.id} (étudiant {cv.etudiant_id})…")
            analyze_cv_background(str(cv.id))
            cv_done += 1

        for ann in db.query(Annonce).filter(Annonce.statut == StatutAnnonce.validee).all():
            needs = force or ann.donnees_ia is None or not _has_embedding(db, SourceType.annonce, ann.id)
            if not needs:
                ann_skip += 1
                continue
            print(f"[ANNONCE] embedding {ann.id} ({ann.titre})…")
            embed_annonce_background(str(ann.id))
            ann_done += 1
    finally:
        db.close()

    print(f"\nTerminé. CV traités={cv_done} ignorés={cv_skip} | "
          f"Annonces traitées={ann_done} ignorées={ann_skip}")


if __name__ == "__main__":
    main(force="--all" in sys.argv)
