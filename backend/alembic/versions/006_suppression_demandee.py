"""Ajout du champ suppression_demandee sur annonces

Revision ID: 006
Revises: 005
"""
from alembic import op
import sqlalchemy as sa

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("annonces", sa.Column("suppression_demandee", sa.Boolean(), nullable=False, server_default="false"))


def downgrade():
    op.drop_column("annonces", "suppression_demandee")
