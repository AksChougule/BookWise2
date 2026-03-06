from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.utils.db import Base


class GenerationSection(StrEnum):
    KEY_IDEAS = "key_ideas"
    CRITIQUE = "critique"


class GenerationStatus(StrEnum):
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class Generation(Base):
    __tablename__ = "generations"
    __table_args__ = (UniqueConstraint("work_id", "section", name="uq_generation_work_section"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    work_id: Mapped[str] = mapped_column(String(64), ForeignKey("books.work_id", ondelete="CASCADE"), index=True)
    section: Mapped[GenerationSection] = mapped_column(
        Enum(GenerationSection, native_enum=False, length=32), nullable=False, index=True
    )
    status: Mapped[GenerationStatus] = mapped_column(
        Enum(GenerationStatus, native_enum=False, length=32), default=GenerationStatus.PENDING, nullable=False
    )
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    prompt_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    input_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    locked_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tokens_prompt: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_completion: Mapped[int | None] = mapped_column(Integer, nullable=True)
    generation_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    book = relationship("Book", back_populates="generations")
