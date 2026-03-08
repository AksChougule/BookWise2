from datetime import UTC, datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.utils.db import Base


class ExploreLink(Base):
    __tablename__ = "explore_links"

    id: Mapped[int] = mapped_column(primary_key=True)
    work_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    amazon_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    goodreads_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    author_website: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )
