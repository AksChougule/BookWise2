"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-03-03 20:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "books",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("work_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("authors", sa.String(length=512), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("cover_url", sa.String(length=512), nullable=True),
        sa.Column("subjects", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_books_work_id"), "books", ["work_id"], unique=True)

    op.create_table(
        "generations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("work_id", sa.String(length=64), nullable=False),
        sa.Column("section", sa.Enum("KEY_IDEAS", "CRITIQUE", name="generationsection", native_enum=False, length=32), nullable=False),
        sa.Column("status", sa.Enum("PENDING", "GENERATING", "COMPLETED", "FAILED", name="generationstatus", native_enum=False, length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("tokens_prompt", sa.Integer(), nullable=True),
        sa.Column("tokens_completion", sa.Integer(), nullable=True),
        sa.Column("generation_time_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["work_id"], ["books.work_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("work_id", "section", name="uq_generation_work_section"),
    )
    op.create_index(op.f("ix_generations_section"), "generations", ["section"], unique=False)
    op.create_index(op.f("ix_generations_work_id"), "generations", ["work_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_generations_work_id"), table_name="generations")
    op.drop_index(op.f("ix_generations_section"), table_name="generations")
    op.drop_table("generations")
    op.drop_index(op.f("ix_books_work_id"), table_name="books")
    op.drop_table("books")
