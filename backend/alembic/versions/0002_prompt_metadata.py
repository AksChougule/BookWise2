"""add prompt metadata columns to generations

Revision ID: 0002_prompt_metadata
Revises: 0001_initial
Create Date: 2026-03-04 00:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0002_prompt_metadata"
down_revision: Union[str, Sequence[str], None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("generations", sa.Column("prompt_name", sa.String(length=128), nullable=True))
    op.add_column("generations", sa.Column("prompt_version", sa.String(length=64), nullable=True))
    op.add_column("generations", sa.Column("prompt_hash", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("generations", "prompt_hash")
    op.drop_column("generations", "prompt_version")
    op.drop_column("generations", "prompt_name")
