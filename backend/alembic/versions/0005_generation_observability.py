"""add generation observability columns

Revision ID: 0005_generation_observability
Revises: 0004_generation_leases
Create Date: 2026-03-05 00:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0005_generation_observability"
down_revision: Union[str, Sequence[str], None] = "0004_generation_leases"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("generations", sa.Column("job_id", sa.String(length=64), nullable=True))
    op.add_column("generations", sa.Column("error_type", sa.String(length=64), nullable=True))
    op.add_column("generations", sa.Column("error_context", sa.Text(), nullable=True))
    op.create_index(op.f("ix_generations_job_id"), "generations", ["job_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_generations_job_id"), table_name="generations")
    op.drop_column("generations", "error_context")
    op.drop_column("generations", "error_type")
    op.drop_column("generations", "job_id")
