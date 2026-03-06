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


def test_claim_job_honors_active_lease_and_allows_reclaim_after_expiry() -> None:
    db = _session()
    try:
        book = Book(work_id="OL1W", title="Book", authors="Author")
        db.add(book)
        db.add(Generation(work_id="OL1W", section=GenerationSection.KEY_IDEAS, status=GenerationStatus.PENDING))
        db.commit()

        repo = GenerationRepository(db)
        assert repo.claim_job(
            work_id="OL1W",
            section=GenerationSection.KEY_IDEAS,
            locked_by="worker-a",
            lease_seconds=100,
        )

        current = repo.get("OL1W", GenerationSection.KEY_IDEAS)
        assert current is not None
        assert current.status == GenerationStatus.GENERATING
        assert current.locked_by == "worker-a"
        assert current.locked_at is not None
        assert current.lease_expires_at is not None

        assert not repo.claim_job(
            work_id="OL1W",
            section=GenerationSection.KEY_IDEAS,
            locked_by="worker-b",
            lease_seconds=100,
        )

        current.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()

        assert repo.claim_job(
            work_id="OL1W",
            section=GenerationSection.KEY_IDEAS,
            locked_by="worker-b",
            lease_seconds=100,
        )
        db.expire_all()
        current = repo.get("OL1W", GenerationSection.KEY_IDEAS)
        assert current is not None
        assert current.locked_by == "worker-b"
    finally:
        db.close()


def test_mark_completed_and_failed_clear_lease_fields() -> None:
    db = _session()
    try:
        book = Book(work_id="OL2W", title="Book", authors="Author")
        db.add(book)
        db.add(Generation(work_id="OL2W", section=GenerationSection.KEY_IDEAS, status=GenerationStatus.PENDING))
        db.add(Generation(work_id="OL2W", section=GenerationSection.CRITIQUE, status=GenerationStatus.PENDING))
        db.commit()

        repo = GenerationRepository(db)

        assert repo.claim_job(
            work_id="OL2W",
            section=GenerationSection.KEY_IDEAS,
            locked_by="worker-a",
            lease_seconds=100,
        )
        completed = repo.mark_completed(
            work_id="OL2W",
            section=GenerationSection.KEY_IDEAS,
            content='{"key_ideas":"x"}',
            prompt_name="key_ideas",
            prompt_version="v1",
            prompt_hash="h",
            idempotency_key="i",
            input_fingerprint="f",
            job_id="job-1",
            model="gpt-5.2",
            tokens_prompt=10,
            tokens_completion=20,
            generation_time_ms=100,
        )
        assert completed.status == GenerationStatus.COMPLETED
        assert completed.locked_by is None
        assert completed.locked_at is None
        assert completed.lease_expires_at is None
        assert completed.finished_at is not None

        assert repo.claim_job(
            work_id="OL2W",
            section=GenerationSection.CRITIQUE,
            locked_by="worker-a",
            lease_seconds=100,
        )
        failed = repo.mark_failed(
            work_id="OL2W",
            section=GenerationSection.CRITIQUE,
            error_message="x",
            prompt_name="critique",
            prompt_version="v1",
            prompt_hash="h",
            idempotency_key="i",
            input_fingerprint="f",
            job_id="job-2",
            model="gpt-5.2",
            generation_time_ms=100,
            error_type="unknown",
            error_context={"reason": "test"},
        )
        assert failed.status == GenerationStatus.FAILED
        assert failed.locked_by is None
        assert failed.locked_at is None
        assert failed.lease_expires_at is None
        assert failed.finished_at is not None
    finally:
        db.close()
