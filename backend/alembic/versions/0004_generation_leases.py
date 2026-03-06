"""add generation lease columns

Revision ID: 0004_generation_leases
Revises: 0003_generation_idempotency
Create Date: 2026-03-05 00:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0004_generation_leases"
down_revision: Union[str, Sequence[str], None] = "0003_generation_idempotency"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("generations", sa.Column("locked_by", sa.String(length=128), nullable=True))
    op.add_column("generations", sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("generations", sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("generations", sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("generations", "finished_at")
    op.drop_column("generations", "lease_expires_at")
    op.drop_column("generations", "locked_at")
    op.drop_column("generations", "locked_by")
