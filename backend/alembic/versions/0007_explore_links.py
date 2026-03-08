"""add explore links table

Revision ID: 0007_explore_links
Revises: 0006_youtube_videos
Create Date: 2026-03-08 09:30:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0007_explore_links"
down_revision: str | Sequence[str] | None = "0006_youtube_videos"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "explore_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("work_id", sa.String(length=64), nullable=False),
        sa.Column("amazon_url", sa.String(length=1024), nullable=False),
        sa.Column("goodreads_url", sa.String(length=1024), nullable=False),
        sa.Column("author_website", sa.String(length=1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("work_id"),
    )
    op.create_index(op.f("ix_explore_links_work_id"), "explore_links", ["work_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_explore_links_work_id"), table_name="explore_links")
    op.drop_table("explore_links")
