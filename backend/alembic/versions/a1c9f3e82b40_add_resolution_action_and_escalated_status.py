"""add_resolution_action_and_escalated_status

Revision ID: a1c9f3e82b40
Revises: fc73863a71f5
Create Date: 2026-06-12 01:00:00.000000

Adds:
  - debates.resolution_action (String, nullable) — stores the Architect's chosen enum value
  - debates.status gains 'escalated' — already handled in the enum; this migration ensures
    the DB column accepts the new value by altering the enum type (Postgres-safe approach).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1c9f3e82b40'
down_revision: Union[str, Sequence[str], None] = 'fc73863a71f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add resolution_action column and 'escalated' to DebateStatus enum."""
    # 1. Add the resolution_action column (free-text string for portability)
    op.add_column(
        'debates',
        sa.Column('resolution_action', sa.String(), nullable=True)
    )

    # 2. Add 'escalated' value to the debatestatus enum in Postgres.
    #    We use a raw SQL approach because SQLAlchemy / Alembic cannot ALTER TYPE
    #    natively without server_default tricks on older versions.
    op.execute("ALTER TYPE debatestatus ADD VALUE IF NOT EXISTS 'escalated'")


def downgrade() -> None:
    """Remove resolution_action column. Note: Postgres cannot remove enum values."""
    op.drop_column('debates', 'resolution_action')
    # NOTE: Postgres does not support removing enum values — the 'escalated'
    # value will remain in the debatestatus enum type after downgrade.
    # This is safe: no rows will reference it after the column is dropped.
