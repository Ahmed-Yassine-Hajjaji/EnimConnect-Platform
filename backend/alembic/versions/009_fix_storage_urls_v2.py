"""fix remaining storage URLs not caught by migration 008

Revision ID: 009
Revises: 008
"""
from alembic import op
import sqlalchemy as sa

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    # Fix any logo_url still not in /api/logos/ format
    conn.execute(
        sa.text("""
            UPDATE entreprises
            SET logo_url = '/api/logos/' || id::text
            WHERE logo_url IS NOT NULL
              AND logo_url NOT LIKE '/api/logos/%'
        """)
    )
    # Fix any photo_url still not in /api/photos/ format
    conn.execute(
        sa.text("""
            UPDATE etudiants
            SET photo_url = '/api/photos/' || id::text
            WHERE photo_url IS NOT NULL
              AND photo_url NOT LIKE '/api/photos/%'
        """)
    )


def downgrade():
    pass
