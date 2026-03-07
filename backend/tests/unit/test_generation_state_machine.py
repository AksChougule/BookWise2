from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.book import Book
from app.models.generation import Generation, GenerationSection, GenerationStatus
from app.repositories.generation_repo import GenerationRepository
from app.utils.db import Base


def _session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    return maker()


def test_pending_to_generating_to_completed() -> None:
    db = _session()
    try:
        db.add(Book(work_id="OLSM1W", title="State Book", authors="Author"))
        db.add(
            Generation(
                work_id="OLSM1W",
                section=GenerationSection.KEY_IDEAS,
                status=GenerationStatus.PENDING,
            )
        )
        db.commit()

        repo = GenerationRepository(db)
        claimed = repo.claim_job(
            work_id="OLSM1W",
            section=GenerationSection.KEY_IDEAS,
            locked_by="worker-a",
            lease_seconds=100,
        )
        assert claimed

        generating = repo.get("OLSM1W", GenerationSection.KEY_IDEAS)
        assert generating is not None
        assert generating.status == GenerationStatus.GENERATING

        completed = repo.mark_completed(
            work_id="OLSM1W",
            section=GenerationSection.KEY_IDEAS,
            content='{"key_ideas":"- one\\n- two"}',
            prompt_name="key_ideas",
            prompt_version="v1",
            prompt_hash="h1",
            idempotency_key="i1",
            input_fingerprint="f1",
            job_id="job-1",
            model="gpt-5.2",
            tokens_prompt=10,
            tokens_completion=20,
            generation_time_ms=100,
        )
        assert completed.status == GenerationStatus.COMPLETED
        assert completed.finished_at is not None
        assert completed.locked_by is None
        assert completed.lease_expires_at is None
    finally:
        db.close()


def test_failed_generation_state() -> None:
    db = _session()
    try:
        db.add(Book(work_id="OLSM2W", title="State Book", authors="Author"))
        db.add(
            Generation(
                work_id="OLSM2W",
                section=GenerationSection.CRITIQUE,
                status=GenerationStatus.PENDING,
            )
        )
        db.commit()

        repo = GenerationRepository(db)
        assert repo.claim_job(
            work_id="OLSM2W",
            section=GenerationSection.CRITIQUE,
            locked_by="worker-a",
            lease_seconds=100,
        )

        failed = repo.mark_failed(
            work_id="OLSM2W",
            section=GenerationSection.CRITIQUE,
            error_message="provider timeout",
            prompt_name="critique",
            prompt_version="v1",
            prompt_hash="h2",
            idempotency_key="i2",
            input_fingerprint="f2",
            job_id="job-2",
            model="gpt-5.2",
            generation_time_ms=200,
            error_type="provider_timeout",
            error_context={"reason": "timeout"},
        )
        assert failed.status == GenerationStatus.FAILED
        assert failed.error_type == "provider_timeout"
        assert failed.finished_at is not None
    finally:
        db.close()


def test_retry_increments_attempt_counter() -> None:
    db = _session()
    try:
        db.add(Book(work_id="OLSM3W", title="State Book", authors="Author"))
        db.add(
            Generation(
                work_id="OLSM3W",
                section=GenerationSection.KEY_IDEAS,
                status=GenerationStatus.PENDING,
            )
        )
        db.commit()

        repo = GenerationRepository(db)
        attempts = 0

        assert repo.claim_job(
            work_id="OLSM3W",
            section=GenerationSection.KEY_IDEAS,
            locked_by="worker-a",
            lease_seconds=100,
        )
        attempts += 1
        repo.mark_failed(
            work_id="OLSM3W",
            section=GenerationSection.KEY_IDEAS,
            error_message="first attempt failed",
            prompt_name="key_ideas",
            prompt_version="v1",
            prompt_hash="h3",
            idempotency_key="i3",
            input_fingerprint="f3",
            job_id="job-3",
            model="gpt-5.2",
            generation_time_ms=120,
            error_type="unknown",
            error_context={"attempt": 1},
        )

        row = repo.get("OLSM3W", GenerationSection.KEY_IDEAS)
        assert row is not None
        row.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()

        assert repo.claim_job(
            work_id="OLSM3W",
            section=GenerationSection.KEY_IDEAS,
            locked_by="worker-b",
            lease_seconds=100,
        )
        attempts += 1

        repo.mark_completed(
            work_id="OLSM3W",
            section=GenerationSection.KEY_IDEAS,
            content='{"key_ideas":"retry success"}',
            prompt_name="key_ideas",
            prompt_version="v1",
            prompt_hash="h3",
            idempotency_key="i3",
            input_fingerprint="f3",
            job_id="job-3",
            model="gpt-5.2",
            tokens_prompt=11,
            tokens_completion=22,
            generation_time_ms=130,
        )

        assert attempts == 2
        final_row = repo.get("OLSM3W", GenerationSection.KEY_IDEAS)
        assert final_row is not None
        assert final_row.status == GenerationStatus.COMPLETED
    finally:
        db.close()
