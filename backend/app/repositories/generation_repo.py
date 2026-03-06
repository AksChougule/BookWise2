from datetime import UTC, datetime, timedelta
import logging

from sqlalchemy import and_, or_, select, update
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

    def get_by_idempotency_key(self, idempotency_key: str) -> Generation | None:
        stmt = select(Generation).where(Generation.idempotency_key == idempotency_key)
        generation = self.db.scalar(stmt)
        logger.info(
            "generation_db_read",
            extra={
                "event": "generation_db_read",
                "action": "by_idempotency_key",
                "idempotency_key": idempotency_key,
                "work_id": generation.work_id if generation else None,
                "section": generation.section.value if generation else None,
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

    def claim_job(self, *, work_id: str, section: GenerationSection, locked_by: str, lease_seconds: int) -> bool:
        now = datetime.now(UTC)
        lease_expires_at = now + timedelta(seconds=lease_seconds)
        stmt = (
            update(Generation)
            .where(
                and_(
                    Generation.work_id == work_id,
                    Generation.section == section,
                    or_(
                        Generation.status.in_([GenerationStatus.PENDING, GenerationStatus.FAILED]),
                        and_(
                            Generation.status == GenerationStatus.GENERATING,
                            or_(Generation.lease_expires_at.is_(None), Generation.lease_expires_at <= now),
                        ),
                    ),
                )
            )
            .values(
                status=GenerationStatus.GENERATING,
                error_message=None,
                locked_by=locked_by,
                locked_at=now,
                lease_expires_at=lease_expires_at,
                finished_at=None,
                updated_at=now,
            )
            .execution_options(synchronize_session=False)
        )
        result = self.db.execute(stmt)
        self.db.commit()
        logger.info(
            "generation_db_commit",
            extra={
                "event": "generation_db_commit",
                "action": "claim_job",
                "work_id": work_id,
                "section": section.value,
                "locked_by": locked_by,
                "lease_seconds": lease_seconds,
                "claimed": result.rowcount > 0,
            },
        )
        return result.rowcount > 0

    def set_idempotency_fields(
        self,
        *,
        work_id: str,
        section: GenerationSection,
        prompt_name: str,
        prompt_version: str,
        prompt_hash: str,
        idempotency_key: str,
        input_fingerprint: str,
    ) -> None:
        stmt = (
            update(Generation)
            .where(and_(Generation.work_id == work_id, Generation.section == section))
            .values(
                prompt_name=prompt_name,
                prompt_version=prompt_version,
                prompt_hash=prompt_hash,
                idempotency_key=idempotency_key,
                input_fingerprint=input_fingerprint,
                updated_at=datetime.now(UTC),
            )
        )
        self.db.execute(stmt)
        self.db.commit()
        logger.info(
            "generation_db_commit",
            extra={
                "event": "generation_db_commit",
                "action": "set_idempotency_fields",
                "work_id": work_id,
                "section": section.value,
                "idempotency_key": idempotency_key,
            },
        )

    def mark_completed(
        self,
        *,
        work_id: str,
        section: GenerationSection,
        content: str,
        prompt_name: str | None,
        prompt_version: str | None,
        prompt_hash: str | None,
        idempotency_key: str | None,
        input_fingerprint: str | None,
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
        generation.idempotency_key = idempotency_key
        generation.input_fingerprint = input_fingerprint
        generation.model = model
        generation.tokens_prompt = tokens_prompt
        generation.tokens_completion = tokens_completion
        generation.generation_time_ms = generation_time_ms
        generation.locked_by = None
        generation.locked_at = None
        generation.lease_expires_at = None
        generation.finished_at = datetime.now(UTC)
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
        idempotency_key: str | None,
        input_fingerprint: str | None,
        model: str | None,
        generation_time_ms: int | None,
    ) -> Generation:
        generation = self.get_or_create(work_id, section)
        generation.status = GenerationStatus.FAILED
        generation.error_message = error_message
        generation.prompt_name = prompt_name
        generation.prompt_version = prompt_version
        generation.prompt_hash = prompt_hash
        generation.idempotency_key = idempotency_key
        generation.input_fingerprint = input_fingerprint
        generation.model = model
        generation.generation_time_ms = generation_time_ms
        generation.locked_by = None
        generation.locked_at = None
        generation.lease_expires_at = None
        generation.finished_at = datetime.now(UTC)
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
