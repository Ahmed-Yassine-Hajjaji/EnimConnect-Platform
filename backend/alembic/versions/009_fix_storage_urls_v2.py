"""reset broken logo/photo URLs so companies can re-upload

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
    # Reset all logo_url — companies will re-upload
    conn.execute(sa.text("UPDATE entreprises SET logo_url = NULL WHERE logo_url IS NOT NULL"))
    # Reset all photo_url — students will re-upload
    conn.execute(sa.text("UPDATE etudiants SET photo_url = NULL WHERE photo_url IS NOT NULL"))


def downgrade():
    pass
