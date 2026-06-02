"""Champs structurés IA (cv/annonce) + index HNSW pgvector pour le matching

Revision ID: 004
Revises: 003
Create Date: 2026-06-02
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Données structurées extraites par l'IA (compétences, niveau, langues, domaines, résumé)
    op.add_column("cvs", sa.Column("donnees_ia", JSONB(), nullable=True))
    op.add_column("annonces", sa.Column("donnees_ia", JSONB(), nullable=True))

    # Index ANN pour la similarité cosinus (pgvector >= 0.5). Accélère le matching
    # et évite de charger tous les vecteurs côté application.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_embeddings_vecteur_hnsw "
        "ON embeddings USING hnsw (vecteur vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_embeddings_vecteur_hnsw")
    op.drop_column("annonces", "donnees_ia")
    op.drop_column("cvs", "donnees_ia")
