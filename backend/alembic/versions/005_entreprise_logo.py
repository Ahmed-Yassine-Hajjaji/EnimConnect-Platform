"""Ajout du champ logo_url pour les entreprises

Revision ID: 005
Revises: 004
Create Date: 2026-06-04
"""
from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("entreprises", sa.Column("logo_url", sa.String(), nullable=True))


def downgrade():
    op.drop_column("entreprises", "logo_url")
