from __future__ import annotations

import json
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.book import Book
from app.models.generation import Generation, GenerationSection, GenerationStatus
from app.providers.openai_provider import OpenAIProvider
from app.repositories.book_repo import BookRepository
from app.repositories.generation_repo import GenerationRepository
from app.schemas.generations import CritiqueOut, CritiquePayload, KeyIdeasOut, KeyIdeasPayload
from app.services.prompt_store import PromptCompileError, PromptStore
from app.utils.db import SessionLocal
from app.utils.logging import now_ms

logger = logging.getLogger(__name__)


class GenerationService:
    def __init__(self, db: Session):
        self.db = db
        self.book_repo = BookRepository(db)
        self.generation_repo = GenerationRepository(db)
        self.provider = OpenAIProvider()
        self.prompt_dir = Path(__file__).resolve().parents[1] / "prompts"
        self.prompt_store = PromptStore(self.prompt_dir)

    @staticmethod
    def _build_context(book: Book) -> tuple[str, str]:
        title = book.title.strip() if book.title else "Untitled"
        author = book.authors.strip() if book.authors else "Unknown"
        return title, author

    @staticmethod
    def _key_ideas_schema() -> dict:
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "key_ideas": {"type": "string"},
            },
            "required": ["key_ideas"],
        }

    @staticmethod
    def _critique_schema() -> dict:
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "strengths": {"type": "string"},
                "weaknesses": {"type": "string"},
                "who_should_read": {"type": "string"},
            },
            "required": ["strengths", "weaknesses", "who_should_read"],
        }

    @staticmethod
    def _parse_content(content: str | None) -> dict:
        if not content:
            return {}
        try:
            parsed = json.loads(content)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}

    @staticmethod
    def _log_snapshot(*, work_id: str, section: GenerationSection, generation: Generation | None) -> None:
        route = f"/api/books/{work_id}/{'key-ideas' if section == GenerationSection.KEY_IDEAS else 'critique'}"
        logger.info(
            "generation_state_snapshot",
            extra={
                "event": "generation_state_snapshot",
                "route": route,
                "work_id": work_id,
                "section": section.value,
                "status": generation.status.value if generation else None,
                "updated_at": generation.updated_at.isoformat() if generation else None,
            },
        )

    @classmethod
    def to_key_ideas_out(cls, generation: Generation) -> KeyIdeasOut:
        content = cls._parse_content(generation.content)
        return KeyIdeasOut(
            work_id=generation.work_id,
            status=generation.status.value,
            section=generation.section.value,
            error_message=generation.error_message,
            prompt_name=generation.prompt_name,
            prompt_version=generation.prompt_version,
            prompt_hash=generation.prompt_hash,
            model=generation.model,
            tokens_prompt=generation.tokens_prompt,
            tokens_completion=generation.tokens_completion,
            generation_time_ms=generation.generation_time_ms,
            updated_at=generation.updated_at,
            key_ideas=content.get("key_ideas") if isinstance(content.get("key_ideas"), str) else None,
        )

    @classmethod
    def to_critique_out(cls, generation: Generation) -> CritiqueOut:
        content = cls._parse_content(generation.content)
        return CritiqueOut(
            work_id=generation.work_id,
            status=generation.status.value,
            section=generation.section.value,
            error_message=generation.error_message,
            prompt_name=generation.prompt_name,
            prompt_version=generation.prompt_version,
            prompt_hash=generation.prompt_hash,
            model=generation.model,
            tokens_prompt=generation.tokens_prompt,
            tokens_completion=generation.tokens_completion,
            generation_time_ms=generation.generation_time_ms,
            updated_at=generation.updated_at,
            strengths=content.get("strengths") if isinstance(content.get("strengths"), str) else None,
            weaknesses=content.get("weaknesses") if isinstance(content.get("weaknesses"), str) else None,
            who_should_read=content.get("who_should_read") if isinstance(content.get("who_should_read"), str) else None,
        )

    async def trigger_key_ideas(self, work_id: str) -> KeyIdeasOut:
        record = self.generation_repo.get_or_create(work_id, GenerationSection.KEY_IDEAS)
        self._log_snapshot(work_id=work_id, section=GenerationSection.KEY_IDEAS, generation=record)

        if record.status == GenerationStatus.COMPLETED:
            return self.to_key_ideas_out(record)

        self.generation_repo.reset_stale_generating(work_id=work_id, section=GenerationSection.KEY_IDEAS)
        record = self.generation_repo.get_or_create(work_id, GenerationSection.KEY_IDEAS)
        self._log_snapshot(work_id=work_id, section=GenerationSection.KEY_IDEAS, generation=record)

        if record.status == GenerationStatus.GENERATING:
            return self.to_key_ideas_out(record)

        if self.generation_repo.claim_for_generation(work_id, GenerationSection.KEY_IDEAS):
            logger.info(
                "generation_started",
                extra={
                    "event": "generation_started",
                    "route": f"/api/books/{work_id}/key-ideas",
                    "work_id": work_id,
                    "section": "key_ideas",
                    "status": "generating",
                },
            )
            await self._run_key_ideas(work_id)
            self.db.expire_all()

        fresh = self.generation_repo.get_or_create(work_id, GenerationSection.KEY_IDEAS)
        self._log_snapshot(work_id=work_id, section=GenerationSection.KEY_IDEAS, generation=fresh)
        return self.to_key_ideas_out(fresh)

    async def get_or_create_critique_status(self, work_id: str) -> CritiqueOut:
        record = self.generation_repo.get_or_create(work_id, GenerationSection.CRITIQUE)
        self._log_snapshot(work_id=work_id, section=GenerationSection.CRITIQUE, generation=record)

        key_ideas = self.generation_repo.get(work_id, GenerationSection.KEY_IDEAS)
        self._log_snapshot(work_id=work_id, section=GenerationSection.KEY_IDEAS, generation=key_ideas)
        if not key_ideas or key_ideas.status != GenerationStatus.COMPLETED:
            return self.to_critique_out(record)

        self.generation_repo.reset_stale_generating(work_id=work_id, section=GenerationSection.CRITIQUE)
        record = self.generation_repo.get_or_create(work_id, GenerationSection.CRITIQUE)
        self._log_snapshot(work_id=work_id, section=GenerationSection.CRITIQUE, generation=record)

        if record.status == GenerationStatus.COMPLETED:
            return self.to_critique_out(record)

        if record.status != GenerationStatus.GENERATING and self.generation_repo.claim_for_generation(
            work_id, GenerationSection.CRITIQUE
        ):
            logger.info(
                "generation_started",
                extra={
                    "event": "generation_started",
                    "route": f"/api/books/{work_id}/critique",
                    "work_id": work_id,
                    "section": "critique",
                    "status": "generating",
                },
            )
            await self._run_critique(work_id)
            self.db.expire_all()

        fresh = self.generation_repo.get_or_create(work_id, GenerationSection.CRITIQUE)
        self._log_snapshot(work_id=work_id, section=GenerationSection.CRITIQUE, generation=fresh)
        return self.to_critique_out(fresh)

    async def _run_key_ideas(self, work_id: str) -> None:
        start_ms = now_ms()
        with SessionLocal() as db:
            book_repo = BookRepository(db)
            generation_repo = GenerationRepository(db)
            book = book_repo.get_by_work_id(work_id)

            if not book:
                generation_repo.mark_failed(
                    work_id=work_id,
                    section=GenerationSection.KEY_IDEAS,
                    error_message="Book metadata not found. Open /api/books/{work_id} first.",
                    prompt_name=None,
                    prompt_version=None,
                    prompt_hash=None,
                    model=self.provider.model,
                    generation_time_ms=now_ms() - start_ms,
                )
                return

            prompt_name = "key_ideas"
            prompt_version: str | None = None
            prompt_hash: str | None = None
            try:
                title, author = self._build_context(book)
                prompt_result = self.prompt_store.render(prompt_name, {"title": title, "author": author})
                prompt = prompt_result.compiled_prompt
                prompt_version = prompt_result.prompt_version
                prompt_hash = prompt_result.prompt_hash
                result = await self.provider.generate_structured(
                    prompt=prompt,
                    schema_name="key_ideas_response",
                    schema=self._key_ideas_schema(),
                    max_output_tokens=5000,
                )
                payload = KeyIdeasPayload.model_validate(result.data)
                completed = generation_repo.mark_completed(
                    work_id=work_id,
                    section=GenerationSection.KEY_IDEAS,
                    content=payload.model_dump_json(),
                    prompt_name=prompt_name,
                    prompt_version=prompt_version,
                    prompt_hash=prompt_hash,
                    model=result.model,
                    tokens_prompt=result.tokens_prompt,
                    tokens_completion=result.tokens_completion,
                    generation_time_ms=now_ms() - start_ms,
                )
                logger.info(
                    "generation_completed",
                    extra={
                        "event": "generation_completed",
                        "route": f"/api/books/{work_id}/key-ideas",
                        "work_id": work_id,
                        "section": "key_ideas",
                        "status": completed.status.value,
                        "model": completed.model,
                        "duration_ms": completed.generation_time_ms,
                        "tokens_prompt": completed.tokens_prompt,
                        "tokens_completion": completed.tokens_completion,
                    },
                )
            except Exception as exc:  # noqa: BLE001
                message = (
                    f"{PromptCompileError.error_type}: {exc}" if isinstance(exc, PromptCompileError) else str(exc)
                )
                failed = generation_repo.mark_failed(
                    work_id=work_id,
                    section=GenerationSection.KEY_IDEAS,
                    error_message=message,
                    prompt_name=prompt_name,
                    prompt_version=prompt_version,
                    prompt_hash=prompt_hash,
                    model=self.provider.model,
                    generation_time_ms=now_ms() - start_ms,
                )
                logger.exception(
                    "generation_failed",
                    extra={
                        "event": "generation_failed",
                        "route": f"/api/books/{work_id}/key-ideas",
                        "work_id": work_id,
                        "section": "key_ideas",
                        "status": failed.status.value,
                        "model": failed.model,
                        "duration_ms": failed.generation_time_ms,
                        "error_message": failed.error_message,
                    },
                )

    async def _run_critique(self, work_id: str) -> None:
        start_ms = now_ms()
        with SessionLocal() as db:
            book_repo = BookRepository(db)
            generation_repo = GenerationRepository(db)

            key_ideas = generation_repo.get(work_id, GenerationSection.KEY_IDEAS)
            if not key_ideas or key_ideas.status != GenerationStatus.COMPLETED:
                generation_repo.mark_failed(
                    work_id=work_id,
                    section=GenerationSection.CRITIQUE,
                    error_message="Cannot generate critique before key ideas are completed.",
                    prompt_name=None,
                    prompt_version=None,
                    prompt_hash=None,
                    model=self.provider.model,
                    generation_time_ms=now_ms() - start_ms,
                )
                return

            book = book_repo.get_by_work_id(work_id)
            if not book:
                generation_repo.mark_failed(
                    work_id=work_id,
                    section=GenerationSection.CRITIQUE,
                    error_message="Book metadata not found.",
                    prompt_name=None,
                    prompt_version=None,
                    prompt_hash=None,
                    model=self.provider.model,
                    generation_time_ms=now_ms() - start_ms,
                )
                return

            prompt_name = "critique"
            prompt_version: str | None = None
            prompt_hash: str | None = None
            try:
                title, author = self._build_context(book)
                prompt_result = self.prompt_store.render(prompt_name, {"title": title, "author": author})
                prompt = prompt_result.compiled_prompt
                prompt_version = prompt_result.prompt_version
                prompt_hash = prompt_result.prompt_hash
                result = await self.provider.generate_structured(
                    prompt=prompt,
                    schema_name="critique_response",
                    schema=self._critique_schema(),
                    max_output_tokens=2000,
                )
                payload = CritiquePayload.model_validate(result.data)
                completed = generation_repo.mark_completed(
                    work_id=work_id,
                    section=GenerationSection.CRITIQUE,
                    content=payload.model_dump_json(),
                    prompt_name=prompt_name,
                    prompt_version=prompt_version,
                    prompt_hash=prompt_hash,
                    model=result.model,
                    tokens_prompt=result.tokens_prompt,
                    tokens_completion=result.tokens_completion,
                    generation_time_ms=now_ms() - start_ms,
                )
                logger.info(
                    "generation_completed",
                    extra={
                        "event": "generation_completed",
                        "route": f"/api/books/{work_id}/critique",
                        "work_id": work_id,
                        "section": "critique",
                        "status": completed.status.value,
                        "model": completed.model,
                        "duration_ms": completed.generation_time_ms,
                        "tokens_prompt": completed.tokens_prompt,
                        "tokens_completion": completed.tokens_completion,
                    },
                )
            except Exception as exc:  # noqa: BLE001
                message = (
                    f"{PromptCompileError.error_type}: {exc}" if isinstance(exc, PromptCompileError) else str(exc)
                )
                failed = generation_repo.mark_failed(
                    work_id=work_id,
                    section=GenerationSection.CRITIQUE,
                    error_message=message,
                    prompt_name=prompt_name,
                    prompt_version=prompt_version,
                    prompt_hash=prompt_hash,
                    model=self.provider.model,
                    generation_time_ms=now_ms() - start_ms,
                )
                logger.exception(
                    "generation_failed",
                    extra={
                        "event": "generation_failed",
                        "route": f"/api/books/{work_id}/critique",
                        "work_id": work_id,
                        "section": "critique",
                        "status": failed.status.value,
                        "model": failed.model,
                        "duration_ms": failed.generation_time_ms,
                        "error_message": failed.error_message,
                    },
                )
