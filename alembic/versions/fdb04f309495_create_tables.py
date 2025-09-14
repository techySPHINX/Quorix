"""
Revision ID: fdb04f309495
Revises: abb11a504be4
Create Date: 2025-09-14 16:06:58.240347+00:00
"""

from __future__ import annotations

# Revision script intentionally minimal; alembic imports kept for API access
import sqlalchemy as sa  # noqa: F401
from alembic import op  # noqa: F401

# revision identifiers, used by Alembic.
revision = "fdb04f309495"
down_revision = "abb11a504be4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
