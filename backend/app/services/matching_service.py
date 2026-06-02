"""Matching hybride : cosinus sémantique (pgvector) + signaux structurés.

Le score combine la similarité d'embeddings et des features explicites
(recouvrement de compétences, niveau, domaines). Les scores numériques ne sont
JAMAIS exposés ; en revanche on renvoie les compétences en correspondance pour
l'explicabilité (chips « Pourquoi ce match »)."""
from typing import List, Tuple, Set, Dict, Optional
import uuid
from sqlalchemy.orm import Session
from app.models.embedding import Embedding, SourceType
from app.models.annonce import Annonce, StatutAnnonce
from app.models.candidature import Candidature

# Pondérations du score hybride (somme = 1)
W_SEMANTIC = 0.55
W_SKILLS = 0.25
W_NIVEAU = 0.10
W_DOMAINES = 0.10


def _norm(s: str) -> str:
    return (s or "").strip().lower()


def _skill_match(cv_skills: List[str], required: List[str]) -> Tuple[float, List[str]]:
    """Retourne (score [0,1], liste des compétences requises en correspondance)."""
    if not required:
        return 0.5, []  # pas d'exigence explicite → neutre
    cv_set = {_norm(s) for s in cv_skills}
    matched = [r for r in required if _norm(r) in cv_set]
    return len(matched) / len(required), matched


def _overlap(a: List[str], b: List[str]) -> float:
    if not a or not b:
        return 0.5  # info absente → neutre
    sa, sb = {_norm(x) for x in a}, {_norm(x) for x in b}
    inter = sa & sb
    return len(inter) / max(len(sa), len(sb)) if inter else 0.0


def _niveau_fit(etudiant_niveau: Optional[str], niveau_requis: Optional[str]) -> float:
    if not niveau_requis:
        return 1.0  # offre ouverte à tous les niveaux
    if not etudiant_niveau:
        return 0.5
    return 1.0 if _norm(etudiant_niveau) == _norm(niveau_requis) else 0.3


def _structured_score(
    cv_donnees: Optional[dict],
    cv_skills_fallback: List[str],
    ann_donnees: Optional[dict],
    etudiant_niveau: Optional[str],
) -> Tuple[float, List[str]]:
    """Score structuré [0,1] (hors sémantique) + compétences en correspondance."""
    cv_donnees = cv_donnees or {}
    ann_donnees = ann_donnees or {}
    cv_skills = cv_donnees.get("competences") or cv_skills_fallback or []
    required = ann_donnees.get("competences_requises") or []

    skill_score, matched = _skill_match(cv_skills, required)
    niveau_score = _niveau_fit(etudiant_niveau, ann_donnees.get("niveau_requis"))
    domaines_score = _overlap(cv_donnees.get("domaines") or [], ann_donnees.get("domaines") or [])

    # Renormalisé sur la part non-sémantique (skills + niveau + domaines)
    total_w = W_SKILLS + W_NIVEAU + W_DOMAINES
    struct = (W_SKILLS * skill_score + W_NIVEAU * niveau_score + W_DOMAINES * domaines_score) / total_w
    return struct, matched


def _cv_semantic_distances(
    db: Session, cv_vec, annonce_ids: List[uuid.UUID]
) -> Dict[uuid.UUID, float]:
    """Distances cosinus (pgvector) entre le CV et chaque annonce, calculées en SQL."""
    if not annonce_ids:
        return {}
    rows = (
        db.query(
            Embedding.source_id,
            Embedding.vecteur.cosine_distance(cv_vec).label("dist"),
        )
        .filter(
            Embedding.source_type == SourceType.annonce,
            Embedding.source_id.in_(annonce_ids),
        )
        .all()
    )
    return {row.source_id: float(row.dist) for row in rows}


def _rank_annonces(
    db: Session, etudiant_id: uuid.UUID, annonces: List[Annonce]
) -> List[Tuple[Annonce, List[str]]]:
    """Classe des annonces pour un étudiant. Retourne (annonce, compétences matchées)."""
    from app.models.cv import CV
    from app.models.etudiant import Etudiant

    if not annonces:
        return []

    etudiant = db.query(Etudiant).filter(Etudiant.id == etudiant_id).first()
    cv = db.query(CV).filter(CV.etudiant_id == etudiant_id).first()
    cv_embedding = None
    if cv:
        cv_embedding = (
            db.query(Embedding)
            .filter(Embedding.source_type == SourceType.cv, Embedding.source_id == cv.id)
            .first()
        )

    # Pas de CV / pas d'embedding → ordre par date (récent d'abord), sans score
    if not cv or not cv_embedding:
        ordered = sorted(annonces, key=lambda a: a.created_at, reverse=True)
        return [(a, []) for a in ordered]

    dist_map = _cv_semantic_distances(db, cv_embedding.vecteur, [a.id for a in annonces])
    cv_skills_fallback = (etudiant.competences if etudiant else None) or []
    etu_niveau = etudiant.niveau if etudiant else None

    scored: List[Tuple[float, Annonce, List[str]]] = []
    for a in annonces:
        dist = dist_map.get(a.id)
        sem = max(0.0, 1.0 - dist) if dist is not None else 0.0  # sim = 1 - distance cosinus
        struct, matched = _structured_score(
            cv.donnees_ia, cv_skills_fallback, a.donnees_ia, etu_niveau
        )
        final = W_SEMANTIC * sem + (1 - W_SEMANTIC) * struct
        scored.append((final, a, matched))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [(a, matched) for _, a, matched in scored]


def get_annonces_sorted_by_cv(
    db: Session, etudiant_id: uuid.UUID
) -> List[Tuple[Annonce, List[str]]]:
    annonces = (
        db.query(Annonce)
        .filter(Annonce.statut == StatutAnnonce.validee, Annonce.is_active == True)
        .all()
    )
    return _rank_annonces(db, etudiant_id, annonces)


def get_annonces_sorted_by_cv_for_dept(
    db: Session, etudiant_id: uuid.UUID, allowed_annonce_ids: Set[str]
) -> List[Tuple[Annonce, List[str]]]:
    if not allowed_annonce_ids:
        return []
    annonces = (
        db.query(Annonce)
        .filter(
            Annonce.statut == StatutAnnonce.validee,
            Annonce.is_active == True,
            Annonce.id.in_([uuid.UUID(aid) for aid in allowed_annonce_ids]),
        )
        .all()
    )
    return _rank_annonces(db, etudiant_id, annonces)


def get_candidats_sorted_by_annonce(
    db: Session, annonce_id: uuid.UUID
) -> List[Tuple[Candidature, object, object, List[str]]]:
    """Classe les candidatures d'une annonce. Retourne (candidature, etudiant, cv, matched)."""
    from app.models.etudiant import Etudiant
    from app.models.cv import CV

    annonce = db.query(Annonce).filter(Annonce.id == annonce_id).first()
    ann_embedding = (
        db.query(Embedding)
        .filter(Embedding.source_type == SourceType.annonce, Embedding.source_id == annonce_id)
        .first()
    )

    candidatures = db.query(Candidature).filter(Candidature.annonce_id == annonce_id).all()
    if not candidatures:
        return []

    etudiant_ids = [c.etudiant_id for c in candidatures]
    etudiants = {e.id: e for e in db.query(Etudiant).filter(Etudiant.id.in_(etudiant_ids)).all()}
    cvs = {cv.etudiant_id: cv for cv in db.query(CV).filter(CV.etudiant_id.in_(etudiant_ids)).all()}

    # Distances cosinus annonce → chaque CV, en une requête SQL
    dist_map: Dict[uuid.UUID, float] = {}
    if ann_embedding:
        cv_ids = [cv.id for cv in cvs.values()]
        if cv_ids:
            rows = (
                db.query(
                    Embedding.source_id,
                    Embedding.vecteur.cosine_distance(ann_embedding.vecteur).label("dist"),
                )
                .filter(Embedding.source_type == SourceType.cv, Embedding.source_id.in_(cv_ids))
                .all()
            )
            dist_map = {row.source_id: float(row.dist) for row in rows}

    ann_donnees = annonce.donnees_ia if annonce else None

    scored = []
    for cand in candidatures:
        etudiant = etudiants.get(cand.etudiant_id)
        cv = cvs.get(cand.etudiant_id)
        sem = 0.0
        if cv is not None and cv.id in dist_map:
            sem = max(0.0, 1.0 - dist_map[cv.id])
        struct, matched = _structured_score(
            cv.donnees_ia if cv else None,
            (etudiant.competences if etudiant else None) or [],
            ann_donnees,
            etudiant.niveau if etudiant else None,
        )
        final = W_SEMANTIC * sem + (1 - W_SEMANTIC) * struct
        scored.append((final, cand, etudiant, cv, matched))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [(cand, etudiant, cv, matched) for _, cand, etudiant, cv, matched in scored]
