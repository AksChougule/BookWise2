from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path

import httpx
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.book import Book
from app.models.generation import Generation, GenerationSection, GenerationStatus
from app.providers.base_provider import ProviderError
from app.providers.openai_provider import OpenAIProvider
from app.repositories.book_repo import BookRepository
from app.repositories.generation_repo import GenerationRepository
from app.schemas.generations import CritiqueOut, CritiquePayload, KeyIdeasOut, KeyIdeasPayload
from app.services.prompt_store import PromptCompileError, PromptStore
from app.utils.db import SessionLocal
from app.utils.idempotency import compute_idempotency_key, compute_input_fingerprint
from app.utils.logging import now_ms

logger = logging.getLogger(__name__)

ERROR_TYPES = {
    "provider_timeout",
    "provider_rate_limited",
    "schema_validation_failed",
    "prompt_compile_error",
    "db_error",
    "unknown",
}


@dataclass(slots=True)
class PreparedPrompt:
    prompt_name: str
    compiled_prompt: str
    prompt_version: str
    prompt_hash: str
    input_fingerprint: str
    idempotency_key: str


class GenerationService:
    def __init__(self, db: Session):
        settings = get_settings()
        self.db = db
        self.book_repo = BookRepository(db)
        self.generation_repo = GenerationRepository(db)
        self.provider = OpenAIProvider()
        self.prompt_dir = Path(__file__).resolve().parents[1] / "prompts"
        self.prompt_store = PromptStore(self.prompt_dir)
        self.lease_seconds = settings.generation_lease_seconds
        self.worker_id = f"pid-{os.getpid()}"

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
    def _error_payload(exc: Exception) -> tuple[str, dict]:
        if isinstance(exc, PromptCompileError):
            return "prompt_compile_error", {"exception": str(exc)}

        if isinstance(exc, ValidationError):
            return "schema_validation_failed", {"validation_errors": exc.errors()}

        if isinstance(exc, ProviderError):
            error_type = exc.error_type if exc.error_type in ERROR_TYPES else "unknown"
            if error_type == "unknown" and "429" in str(exc):
                error_type = "provider_rate_limited"
            context = dict(exc.error_context)
            context.setdefault("exception", str(exc))
            return error_type, context

        if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError)):
            return "provider_timeout", {"exception": str(exc)}

        if isinstance(exc, SQLAlchemyError):
            return "db_error", {"exception": str(exc)}

        return "unknown", {"exception": str(exc)}

    def _prepare_prompt(
        self,
        *,
        book: Book,
        work_id: str,
        section: GenerationSection,
        prompt_name: str,
    ) -> PreparedPrompt:
        title, author = self._build_context(book)
        prompt_result = self.prompt_store.render(prompt_name, {"title": title, "author": author})
        input_fingerprint = compute_input_fingerprint(
            title=book.title,
            authors=book.authors,
            description=book.description,
        )
        idempotency_key = compute_idempotency_key(
            work_id=work_id,
            section=section.value,
            prompt_hash=prompt_result.prompt_hash,
            model=self.provider.model,
        )
        return PreparedPrompt(
            prompt_name=prompt_name,
            compiled_prompt=prompt_result.compiled_prompt,
            prompt_version=prompt_result.prompt_version,
            prompt_hash=prompt_result.prompt_hash,
            input_fingerprint=input_fingerprint,
            idempotency_key=idempotency_key,
        )

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
                "job_id": generation.job_id if generation else None,
                "status": generation.status.value if generation else None,
                "updated_at": generation.updated_at.isoformat() if generation else None,
            },
        )

    @staticmethod
    def _log_metric_event(
        *,
        event: str,
        route: str,
        work_id: str,
        section: str,
        job_id: str | None,
        model: str | None,
        latency_ms: int | None,
        tokens_prompt: int | None,
        tokens_completion: int | None,
        status: str | None = None,
        error_type: str | None = None,
        error_message: str | None = None,
    ) -> None:
        logger.info(
            event,
            extra={
                "event": event,
                "route": route,
                "work_id": work_id,
                "section": section,
                "job_id": job_id,
                "status": status,
                "model": model,
                "latency_ms": latency_ms,
                "tokens_prompt": tokens_prompt,
                "tokens_completion": tokens_completion,
                "error_type": error_type,
                "error_message": error_message,
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
        book = self.book_repo.get_by_work_id(work_id)
        if not book:
            record = self.generation_repo.get_or_create(work_id, GenerationSection.KEY_IDEAS)
            return self.to_key_ideas_out(record)

        prepared = self._prepare_prompt(
            book=book,
            work_id=work_id,
            section=GenerationSection.KEY_IDEAS,
            prompt_name="key_ideas",
        )
        existing_for_key = self.generation_repo.get_by_idempotency_key(prepared.idempotency_key)
        if existing_for_key:
            self._log_snapshot(work_id=work_id, section=GenerationSection.KEY_IDEAS, generation=existing_for_key)
            return self.to_key_ideas_out(existing_for_key)

        record = self.generation_repo.get_or_create(work_id, GenerationSection.KEY_IDEAS)
        job_id = self.generation_repo.ensure_job_id(work_id=work_id, section=GenerationSection.KEY_IDEAS)
        self.generation_repo.set_idempotency_fields(
            work_id=work_id,
            section=GenerationSection.KEY_IDEAS,
            prompt_name=prepared.prompt_name,
            prompt_version=prepared.prompt_version,
            prompt_hash=prepared.prompt_hash,
            idempotency_key=prepared.idempotency_key,
            input_fingerprint=prepared.input_fingerprint,
        )
        self._log_snapshot(work_id=work_id, section=GenerationSection.KEY_IDEAS, generation=record)

        if record.status == GenerationStatus.COMPLETED:
            return self.to_key_ideas_out(record)

        if self.generation_repo.claim_job(
            work_id=work_id,
            section=GenerationSection.KEY_IDEAS,
            locked_by=self.worker_id,
            lease_seconds=self.lease_seconds,
        ):
            self._log_metric_event(
                event="generation_started",
                route=f"/api/books/{work_id}/key-ideas",
                work_id=work_id,
                section=GenerationSection.KEY_IDEAS.value,
                job_id=job_id,
                model=self.provider.model,
                latency_ms=0,
                tokens_prompt=None,
                tokens_completion=None,
                status="generating",
            )
            await self._run_key_ideas(work_id, job_id=job_id, prepared=prepared)
            self.db.expire_all()

        fresh = self.generation_repo.get(work_id, GenerationSection.KEY_IDEAS)
        self._log_snapshot(work_id=work_id, section=GenerationSection.KEY_IDEAS, generation=fresh)
        if fresh is None:
            fresh = self.generation_repo.get_or_create(work_id, GenerationSection.KEY_IDEAS)
        return self.to_key_ideas_out(fresh)

    async def get_or_create_critique_status(self, work_id: str) -> CritiqueOut:
        record = self.generation_repo.get_or_create(work_id, GenerationSection.CRITIQUE)
        self._log_snapshot(work_id=work_id, section=GenerationSection.CRITIQUE, generation=record)

        key_ideas = self.generation_repo.get(work_id, GenerationSection.KEY_IDEAS)
        self._log_snapshot(work_id=work_id, section=GenerationSection.KEY_IDEAS, generation=key_ideas)
        if not key_ideas or key_ideas.status != GenerationStatus.COMPLETED:
            return self.to_critique_out(record)

        book = self.book_repo.get_by_work_id(work_id)
        if not book:
            return self.to_critique_out(record)

        prepared = self._prepare_prompt(
            book=book,
            work_id=work_id,
            section=GenerationSection.CRITIQUE,
            prompt_name="critique",
        )
        existing_for_key = self.generation_repo.get_by_idempotency_key(prepared.idempotency_key)
        if existing_for_key:
            self._log_snapshot(work_id=work_id, section=GenerationSection.CRITIQUE, generation=existing_for_key)
            return self.to_critique_out(existing_for_key)

        record = self.generation_repo.get_or_create(work_id, GenerationSection.CRITIQUE)
        job_id = self.generation_repo.ensure_job_id(work_id=work_id, section=GenerationSection.CRITIQUE)
        self.generation_repo.set_idempotency_fields(
            work_id=work_id,
            section=GenerationSection.CRITIQUE,
            prompt_name=prepared.prompt_name,
            prompt_version=prepared.prompt_version,
            prompt_hash=prepared.prompt_hash,
            idempotency_key=prepared.idempotency_key,
            input_fingerprint=prepared.input_fingerprint,
        )
        self._log_snapshot(work_id=work_id, section=GenerationSection.CRITIQUE, generation=record)

        if record.status == GenerationStatus.COMPLETED:
            return self.to_critique_out(record)

        if self.generation_repo.claim_job(
            work_id=work_id,
            section=GenerationSection.CRITIQUE,
            locked_by=self.worker_id,
            lease_seconds=self.lease_seconds,
        ):
            self._log_metric_event(
                event="generation_started",
                route=f"/api/books/{work_id}/critique",
                work_id=work_id,
                section=GenerationSection.CRITIQUE.value,
                job_id=job_id,
                model=self.provider.model,
                latency_ms=0,
                tokens_prompt=None,
                tokens_completion=None,
                status="generating",
            )
            await self._run_critique(work_id, job_id=job_id, prepared=prepared)
            self.db.expire_all()

        fresh = self.generation_repo.get(work_id, GenerationSection.CRITIQUE)
        self._log_snapshot(work_id=work_id, section=GenerationSection.CRITIQUE, generation=fresh)
        if fresh is None:
            fresh = self.generation_repo.get_or_create(work_id, GenerationSection.CRITIQUE)
        return self.to_critique_out(fresh)

    async def _run_key_ideas(self, work_id: str, *, job_id: str, prepared: PreparedPrompt | None = None) -> None:
        start_ms = now_ms()
        route = f"/api/books/{work_id}/key-ideas"
        with SessionLocal() as db:
            book_repo = BookRepository(db)
            generation_repo = GenerationRepository(db)
            book = book_repo.get_by_work_id(work_id)

            if not book:
                failed = generation_repo.mark_failed(
                    work_id=work_id,
                    section=GenerationSection.KEY_IDEAS,
                    error_message="Book metadata not found. Open /api/books/{work_id} first.",
                    prompt_name=None,
                    prompt_version=None,
                    prompt_hash=None,
                    idempotency_key=None,
                    input_fingerprint=None,
                    job_id=job_id,
                    model=self.provider.model,
                    generation_time_ms=now_ms() - start_ms,
                    error_type="unknown",
                    error_context={"reason": "book_missing"},
                )
                self._log_metric_event(
                    event="generation_failed",
                    route=route,
                    work_id=work_id,
                    section=GenerationSection.KEY_IDEAS.value,
                    job_id=job_id,
                    model=self.provider.model,
                    latency_ms=failed.generation_time_ms,
                    tokens_prompt=None,
                    tokens_completion=None,
                    status=failed.status.value,
                    error_type="unknown",
                    error_message=failed.error_message,
                )
                return

            prompt_name = "key_ideas"
            prompt_version: str | None = prepared.prompt_version if prepared else None
            prompt_hash: str | None = prepared.prompt_hash if prepared else None
            idempotency_key: str | None = prepared.idempotency_key if prepared else None
            input_fingerprint: str | None = prepared.input_fingerprint if prepared else None
            try:
                if prepared is None:
                    prepared = self._prepare_prompt(
                        book=book,
                        work_id=work_id,
                        section=GenerationSection.KEY_IDEAS,
                        prompt_name=prompt_name,
                    )
                    prompt_version = prepared.prompt_version
                    prompt_hash = prepared.prompt_hash
                    idempotency_key = prepared.idempotency_key
                    input_fingerprint = prepared.input_fingerprint
                prompt = prepared.compiled_prompt
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
                    idempotency_key=idempotency_key,
                    input_fingerprint=input_fingerprint,
                    job_id=job_id,
                    model=result.model,
                    tokens_prompt=result.tokens_prompt,
                    tokens_completion=result.tokens_completion,
                    generation_time_ms=now_ms() - start_ms,
                )
                self._log_metric_event(
                    event="generation_completed",
                    route=route,
                    work_id=work_id,
                    section=GenerationSection.KEY_IDEAS.value,
                    job_id=completed.job_id,
                    model=completed.model,
                    latency_ms=completed.generation_time_ms,
                    tokens_prompt=completed.tokens_prompt,
                    tokens_completion=completed.tokens_completion,
                    status=completed.status.value,
                )
            except Exception as exc:  # noqa: BLE001
                error_type, error_context = self._error_payload(exc)
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
                    idempotency_key=idempotency_key,
                    input_fingerprint=input_fingerprint,
                    job_id=job_id,
                    model=self.provider.model,
                    generation_time_ms=now_ms() - start_ms,
                    error_type=error_type,
                    error_context=error_context,
                )
                self._log_metric_event(
                    event="generation_failed",
                    route=route,
                    work_id=work_id,
                    section=GenerationSection.KEY_IDEAS.value,
                    job_id=failed.job_id,
                    model=failed.model,
                    latency_ms=failed.generation_time_ms,
                    tokens_prompt=None,
                    tokens_completion=None,
                    status=failed.status.value,
                    error_type=error_type,
                    error_message=failed.error_message,
                )
                logger.exception(
                    "generation_failed",
                    extra={
                        "event": "generation_failed",
                        "route": route,
                        "work_id": work_id,
                        "section": GenerationSection.KEY_IDEAS.value,
                        "job_id": failed.job_id,
                        "status": failed.status.value,
                        "model": failed.model,
                        "latency_ms": failed.generation_time_ms,
                        "error_type": error_type,
                        "error_message": failed.error_message,
                    },
                )

    async def _run_critique(self, work_id: str, *, job_id: str, prepared: PreparedPrompt | None = None) -> None:
        start_ms = now_ms()
        route = f"/api/books/{work_id}/critique"
        with SessionLocal() as db:
            book_repo = BookRepository(db)
            generation_repo = GenerationRepository(db)

            key_ideas = generation_repo.get(work_id, GenerationSection.KEY_IDEAS)
            if not key_ideas or key_ideas.status != GenerationStatus.COMPLETED:
                failed = generation_repo.mark_failed(
                    work_id=work_id,
                    section=GenerationSection.CRITIQUE,
                    error_message="Cannot generate critique before key ideas are completed.",
                    prompt_name=None,
                    prompt_version=None,
                    prompt_hash=None,
                    idempotency_key=None,
                    input_fingerprint=None,
                    job_id=job_id,
                    model=self.provider.model,
                    generation_time_ms=now_ms() - start_ms,
                    error_type="unknown",
                    error_context={"reason": "key_ideas_not_completed"},
                )
                self._log_metric_event(
                    event="generation_failed",
                    route=route,
                    work_id=work_id,
                    section=GenerationSection.CRITIQUE.value,
                    job_id=job_id,
                    model=self.provider.model,
                    latency_ms=failed.generation_time_ms,
                    tokens_prompt=None,
                    tokens_completion=None,
                    status=failed.status.value,
                    error_type="unknown",
                    error_message=failed.error_message,
                )
                return

            book = book_repo.get_by_work_id(work_id)
            if not book:
                failed = generation_repo.mark_failed(
                    work_id=work_id,
                    section=GenerationSection.CRITIQUE,
                    error_message="Book metadata not found.",
                    prompt_name=None,
                    prompt_version=None,
                    prompt_hash=None,
                    idempotency_key=None,
                    input_fingerprint=None,
                    job_id=job_id,
                    model=self.provider.model,
                    generation_time_ms=now_ms() - start_ms,
                    error_type="unknown",
                    error_context={"reason": "book_missing"},
                )
                self._log_metric_event(
                    event="generation_failed",
                    route=route,
                    work_id=work_id,
                    section=GenerationSection.CRITIQUE.value,
                    job_id=job_id,
                    model=self.provider.model,
                    latency_ms=failed.generation_time_ms,
                    tokens_prompt=None,
                    tokens_completion=None,
                    status=failed.status.value,
                    error_type="unknown",
                    error_message=failed.error_message,
                )
                return

            prompt_name = "critique"
            prompt_version: str | None = prepared.prompt_version if prepared else None
            prompt_hash: str | None = prepared.prompt_hash if prepared else None
            idempotency_key: str | None = prepared.idempotency_key if prepared else None
            input_fingerprint: str | None = prepared.input_fingerprint if prepared else None
            try:
                if prepared is None:
                    prepared = self._prepare_prompt(
                        book=book,
                        work_id=work_id,
                        section=GenerationSection.CRITIQUE,
                        prompt_name=prompt_name,
                    )
                    prompt_version = prepared.prompt_version
                    prompt_hash = prepared.prompt_hash
                    idempotency_key = prepared.idempotency_key
                    input_fingerprint = prepared.input_fingerprint
                prompt = prepared.compiled_prompt
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
                    idempotency_key=idempotency_key,
                    input_fingerprint=input_fingerprint,
                    job_id=job_id,
                    model=result.model,
                    tokens_prompt=result.tokens_prompt,
                    tokens_completion=result.tokens_completion,
                    generation_time_ms=now_ms() - start_ms,
                )
                self._log_metric_event(
                    event="generation_completed",
                    route=route,
                    work_id=work_id,
                    section=GenerationSection.CRITIQUE.value,
                    job_id=completed.job_id,
                    model=completed.model,
                    latency_ms=completed.generation_time_ms,
                    tokens_prompt=completed.tokens_prompt,
                    tokens_completion=completed.tokens_completion,
                    status=completed.status.value,
                )
            except Exception as exc:  # noqa: BLE001
                error_type, error_context = self._error_payload(exc)
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
                    idempotency_key=idempotency_key,
                    input_fingerprint=input_fingerprint,
                    job_id=job_id,
                    model=self.provider.model,
                    generation_time_ms=now_ms() - start_ms,
                    error_type=error_type,
                    error_context=error_context,
                )
                self._log_metric_event(
                    event="generation_failed",
                    route=route,
                    work_id=work_id,
                    section=GenerationSection.CRITIQUE.value,
                    job_id=failed.job_id,
                    model=failed.model,
                    latency_ms=failed.generation_time_ms,
                    tokens_prompt=None,
                    tokens_completion=None,
                    status=failed.status.value,
                    error_type=error_type,
                    error_message=failed.error_message,
                )
                logger.exception(
                    "generation_failed",
                    extra={
                        "event": "generation_failed",
                        "route": route,
                        "work_id": work_id,
                        "section": GenerationSection.CRITIQUE.value,
                        "job_id": failed.job_id,
                        "status": failed.status.value,
                        "model": failed.model,
                        "latency_ms": failed.generation_time_ms,
                        "error_type": error_type,
                        "error_message": failed.error_message,
                    },
                )
