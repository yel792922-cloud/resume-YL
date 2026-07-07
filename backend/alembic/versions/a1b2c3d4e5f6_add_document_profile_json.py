"""add documents.profile_json (report profile hint/inference)

Revision ID: a1b2c3d4e5f6
Revises: edb1eb3c08b3
Create Date: 2026-07-07 08:20:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "a1b2c3d4e5f6"
down_revision = "edb1eb3c08b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Nullable so existing rows are unaffected (NULL → auto-detect at read time).
    op.add_column("documents", sa.Column("profile_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("documents", "profile_json")
