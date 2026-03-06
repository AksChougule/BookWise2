"""add idempotency columns to generations

Revision ID: 0003_generation_idempotency
Revises: 0002_prompt_metadata
Create Date: 2026-03-05 00:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0003_generation_idempotency"
down_revision: Union[str, Sequence[str], None] = "0002_prompt_metadata"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("generations", sa.Column("idempotency_key", sa.String(length=64), nullable=True))
    op.add_column("generations", sa.Column("input_fingerprint", sa.String(length=64), nullable=True))
    op.create_index(op.f("ix_generations_idempotency_key"), "generations", ["idempotency_key"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_generations_idempotency_key"), table_name="generations")
    op.drop_column("generations", "input_fingerprint")
    op.drop_column("generations", "idempotency_key")
