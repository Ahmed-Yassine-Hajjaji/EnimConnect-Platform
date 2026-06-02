"""Extraction structurée via gpt-4o-mini (mode JSON) — alimente le matching ET
l'affichage lisible côté recruteur. Inclut un retry/backoff sur les appels OpenAI."""
import json
import logging
import time
from typing import Callable, TypeVar, List, Dict, Any

from openai import OpenAI
from app.config import settings

logger = logging.getLogger(__name__)
client = OpenAI(api_key=settings.OPENAI_API_KEY)

CHAT_MODEL = "gpt-4o-mini"

T = TypeVar("T")


def with_retry(fn: Callable[[], T], *, attempts: int = 3, base_delay: float = 1.0) -> T:
    """Exécute fn avec retry exponentiel sur erreur transitoire OpenAI."""
    last_exc: Exception | None = None
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001 — on relance après les tentatives
            last_exc = e
            if i < attempts - 1:
                time.sleep(base_delay * (2 ** i))
                logger.warning("[ai] tentative %d échouée (%s), nouvel essai…", i + 1, e)
    assert last_exc is not None
    raise last_exc


def _chat_json(system: str, user: str, max_tokens: int = 500) -> Dict[str, Any]:
    def call() -> Dict[str, Any]:
        resp = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
            max_tokens=max_tokens,
            temperature=0.1,
        )
        return json.loads(resp.choices[0].message.content or "{}")

    try:
        return with_retry(call)
    except Exception as e:  # noqa: BLE001
        logger.error("[ai] échec extraction JSON: %s", e)
        return {}


def _as_str_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str) and value.strip():
        return [p.strip() for p in value.split(",") if p.strip()]
    return []


# ─── CV ────────────────────────────────────────────────────────────────────────

_CV_SYSTEM = """Tu es un expert RH. À partir du texte brut d'un CV d'étudiant ingénieur (ENSMR), \
renvoie UNIQUEMENT un objet JSON avec ces clés :
- "resume": 2 à 3 phrases en français, lisibles par un recruteur, décrivant le profil \
(PAS une liste de mots-clés, du texte rédigé et professionnel).
- "competences": liste de compétences techniques normalisées (langages, frameworks, outils). Ex: ["Python","React","SQL"].
- "langues": liste de chaînes "Langue (niveau)". Ex: ["Français (C1)","Anglais (B2)"].
- "domaines": 2 à 4 domaines/secteurs d'intérêt. Ex: ["data science","développement web"].
- "niveau": "1A", "2A", "3A" ou "" si inconnu.
- "filiere": filière/spécialité si mentionnée, sinon "".
Réponds en JSON valide, sans texte autour."""


def analyze_cv_structured(cv_text: str) -> Dict[str, Any]:
    if not cv_text or not cv_text.strip():
        return {}
    data = _chat_json(_CV_SYSTEM, cv_text[:6000], max_tokens=600)
    return {
        "resume": (data.get("resume") or "").strip(),
        "competences": _as_str_list(data.get("competences")),
        "langues": _as_str_list(data.get("langues")),
        "domaines": _as_str_list(data.get("domaines")),
        "niveau": (data.get("niveau") or "").strip(),
        "filiere": (data.get("filiere") or "").strip(),
    }


def build_cv_embedding_text(donnees: Dict[str, Any], fallback_text: str = "") -> str:
    if not donnees:
        return fallback_text
    parts = [
        donnees.get("resume", ""),
        "Compétences: " + ", ".join(donnees.get("competences", [])),
        "Domaines: " + ", ".join(donnees.get("domaines", [])),
        f"Niveau: {donnees.get('niveau', '')} {donnees.get('filiere', '')}".strip(),
        "Langues: " + ", ".join(donnees.get("langues", [])),
    ]
    text = "\n".join(p for p in parts if p and p not in ("Compétences: ", "Domaines: ", "Langues: "))
    return text.strip() or fallback_text


# ─── Annonce ─────────────────────────────────────────────────────────────────────

_ANNONCE_SYSTEM = """Tu es un expert RH. À partir du titre et de la description d'une offre de stage, \
renvoie UNIQUEMENT un objet JSON avec ces clés :
- "resume": 1 à 2 phrases résumant l'offre.
- "competences_requises": liste normalisée des compétences attendues. Ex: ["Python","SQL","Power BI"].
- "niveau_requis": "1A", "2A", "3A" ou "" si non précisé.
- "domaines": 2 à 4 domaines de l'offre.
Réponds en JSON valide, sans texte autour."""


def analyze_annonce_structured(titre: str, description: str) -> Dict[str, Any]:
    user = f"Titre: {titre}\nDescription: {description}"[:6000]
    data = _chat_json(_ANNONCE_SYSTEM, user, max_tokens=400)
    return {
        "resume": (data.get("resume") or "").strip(),
        "competences_requises": _as_str_list(data.get("competences_requises")),
        "niveau_requis": (data.get("niveau_requis") or "").strip(),
        "domaines": _as_str_list(data.get("domaines")),
    }


def build_annonce_embedding_text(titre: str, description: str, donnees: Dict[str, Any]) -> str:
    parts = [titre, description]
    if donnees:
        if donnees.get("competences_requises"):
            parts.append("Compétences requises: " + ", ".join(donnees["competences_requises"]))
        if donnees.get("domaines"):
            parts.append("Domaines: " + ", ".join(donnees["domaines"]))
    return "\n".join(p for p in parts if p).strip()
