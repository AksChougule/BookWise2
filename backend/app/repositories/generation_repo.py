from datetime import UTC, datetime
import logging

from sqlalchemy import and_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.generation import Generation, GenerationSection, GenerationStatus

logger = logging.getLogger(__name__)


class GenerationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, work_id: str, section: GenerationSection) -> Generation | None:
        stmt = select(Generation).where(and_(Generation.work_id == work_id, Generation.section == section))
        generation = self.db.scalar(stmt)
        logger.info(
            "generation_db_read",
            extra={
                "event": "generation_db_read",
                "work_id": work_id,
                "section": section.value,
                "status": generation.status.value if generation else None,
            },
        )
        return generation

    def get_or_create(self, work_id: str, section: GenerationSection) -> Generation:
        existing = self.get(work_id, section)
        if existing:
            return existing

        generation = Generation(work_id=work_id, section=section, status=GenerationStatus.PENDING)
        self.db.add(generation)
        try:
            self.db.commit()
            self.db.refresh(generation)
            logger.info(
                "generation_db_commit",
                extra={
                    "event": "generation_db_commit",
                    "action": "insert_pending",
                    "work_id": work_id,
                    "section": section.value,
                    "status": generation.status.value,
                },
            )
            return generation
        except IntegrityError:
            self.db.rollback()
            current = self.get(work_id, section)
            if current is None:
                raise
            return current

    def claim_for_generation(self, work_id: str, section: GenerationSection) -> bool:
        stmt = (
            update(Generation)
            .where(
                and_(
                    Generation.work_id == work_id,
                    Generation.section == section,
                    Generation.status.in_([GenerationStatus.PENDING, GenerationStatus.FAILED]),
                )
            )
            .values(
                status=GenerationStatus.GENERATING,
                error_message=None,
                updated_at=datetime.now(UTC),
            )
        )
        result = self.db.execute(stmt)
        self.db.commit()
        logger.info(
            "generation_db_commit",
            extra={
                "event": "generation_db_commit",
                "action": "claim_for_generation",
                "work_id": work_id,
                "section": section.value,
                "claimed": result.rowcount > 0,
            },
        )
        return result.rowcount > 0

    def reset_stale_generating(
        self,
        *,
        work_id: str,
        section: GenerationSection,
        stale_after_seconds: int = 180,
        reason: str = "Generation attempt became stale and was reset.",
    ) -> bool:
        cutoff = datetime.now(UTC).timestamp() - stale_after_seconds
        cutoff_dt = datetime.fromtimestamp(cutoff, tz=UTC).replace(tzinfo=None)
        stmt = (
            update(Generation)
            .where(
                and_(
                    Generation.work_id == work_id,
                    Generation.section == section,
                    Generation.status == GenerationStatus.GENERATING,
                    Generation.updated_at < cutoff_dt,
                )
            )
            .values(
                status=GenerationStatus.FAILED,
                error_message=reason,
                updated_at=datetime.now(UTC).replace(tzinfo=None),
            )
        )
        result = self.db.execute(stmt)
        self.db.commit()
        if result.rowcount > 0:
            logger.warning(
                "generation_db_commit",
                extra={
                    "event": "generation_db_commit",
                    "action": "reset_stale_generating",
                    "work_id": work_id,
                    "section": section.value,
                    "stale_after_seconds": stale_after_seconds,
                },
            )
        return result.rowcount > 0

    def mark_completed(
        self,
        *,
        work_id: str,
        section: GenerationSection,
        content: str,
        prompt_name: str | None,
        prompt_version: str | None,
        prompt_hash: str | None,
        model: str,
        tokens_prompt: int | None,
        tokens_completion: int | None,
        generation_time_ms: int,
    ) -> Generation:
        generation = self.get_or_create(work_id, section)
        generation.status = GenerationStatus.COMPLETED
        generation.content = content
        generation.error_message = None
        generation.prompt_name = prompt_name
        generation.prompt_version = prompt_version
        generation.prompt_hash = prompt_hash
        generation.model = model
        generation.tokens_prompt = tokens_prompt
        generation.tokens_completion = tokens_completion
        generation.generation_time_ms = generation_time_ms
        self.db.commit()
        self.db.refresh(generation)
        logger.info(
            "generation_db_commit",
            extra={
                "event": "generation_db_commit",
                "action": "mark_completed",
                "work_id": work_id,
                "section": section.value,
                "status": generation.status.value,
            },
        )
        return generation

    def mark_failed(
        self,
        *,
        work_id: str,
        section: GenerationSection,
        error_message: str,
        prompt_name: str | None,
        prompt_version: str | None,
        prompt_hash: str | None,
        model: str | None,
        generation_time_ms: int | None,
    ) -> Generation:
        generation = self.get_or_create(work_id, section)
        generation.status = GenerationStatus.FAILED
        generation.error_message = error_message
        generation.prompt_name = prompt_name
        generation.prompt_version = prompt_version
        generation.prompt_hash = prompt_hash
        generation.model = model
        generation.generation_time_ms = generation_time_ms
        self.db.commit()
        self.db.refresh(generation)
        logger.info(
            "generation_db_commit",
            extra={
                "event": "generation_db_commit",
                "action": "mark_failed",
                "work_id": work_id,
                "section": section.value,
                "status": generation.status.value,
            },
        )
        return generation
