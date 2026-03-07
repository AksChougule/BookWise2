"""add youtube videos cache table

Revision ID: 0006_youtube_videos
Revises: 0005_generation_observability
Create Date: 2026-03-07 15:05:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0006_youtube_videos"
down_revision: str | Sequence[str] | None = "0005_generation_observability"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "youtube_videos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("work_id", sa.String(length=64), nullable=False),
        sa.Column("video_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("channel", sa.String(length=256), nullable=False),
        sa.Column("views", sa.Integer(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("thumbnail", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("work_id", "video_id", name="uq_youtube_work_video"),
    )
    op.create_index(op.f("ix_youtube_videos_work_id"), "youtube_videos", ["work_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_youtube_videos_work_id"), table_name="youtube_videos")
    op.drop_table("youtube_videos")
