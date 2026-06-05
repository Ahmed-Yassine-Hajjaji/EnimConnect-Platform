"""migrate storage URLs from /storage/ to /api/

Revision ID: 008
Revises: 007
"""
from alembic import op
import sqlalchemy as sa

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    # Fix logo_url: /storage/logos/UUID.ext -> /api/logos/UUID
    conn.execute(
        sa.text("""
            UPDATE entreprises
            SET logo_url = '/api/logos/' || id::text
            WHERE logo_url IS NOT NULL AND logo_url LIKE '/storage/logos/%'
        """)
    )
    # Fix photo_url: /storage/photos/UUID.ext -> /api/photos/UUID
    conn.execute(
        sa.text("""
            UPDATE etudiants
            SET photo_url = '/api/photos/' || id::text
            WHERE photo_url IS NOT NULL AND photo_url LIKE '/storage/photos/%'
        """)
    )


def downgrade():
    pass
