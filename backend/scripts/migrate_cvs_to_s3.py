"""Migration des CV du disque local vers Amazon S3.

À lancer une seule fois, après avoir configuré les variables S3 dans .env
(STORAGE_BACKEND=s3, S3_BUCKET, AWS_*). Idempotent : ne renvoie vers S3 que les
CV présents sur le disque, et met à jour cv.fichier_url avec la référence S3.

Usage (depuis backend/) :
  python scripts/migrate_cvs_to_s3.py            # migre
  python scripts/migrate_cvs_to_s3.py --dry-run  # liste sans rien copier
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.cv import CV
from app.services import storage_service
from app.config import settings


def main(dry_run: bool = False) -> None:
    if not storage_service.is_s3() and not dry_run:
        print("STORAGE_BACKEND n'est pas 's3' — configure le .env avant de migrer.")
        sys.exit(1)

    db = SessionLocal()
    migres = absents = deja = 0
    try:
        for cv in db.query(CV).all():
            eid = str(cv.etudiant_id)
            local_path = storage_service.local_cv_path(eid)
            if not os.path.exists(local_path):
                absents += 1
                continue
            if storage_service.cv_exists(eid):
                deja += 1
                continue
            print(f"[MIGRATE] {eid}")
            if not dry_run:
                with open(local_path, "rb") as f:
                    ref = storage_service.save_cv(eid, f.read())
                cv.fichier_url = ref
                db.add(cv)
            migres += 1
        if not dry_run:
            db.commit()
    finally:
        db.close()

    print(f"\nTerminé. Migrés={migres} | déjà sur S3={deja} | fichier local absent={absents}")
    if dry_run:
        print("(dry-run : aucune copie effectuée)")


if __name__ == "__main__":
    main(dry_run="--dry-run" in sys.argv)
