import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.generation import GenerationSection, GenerationStatus
from app.repositories.book_repo import BookRepository
from app.repositories.generation_repo import GenerationRepository


def _run_migrations(db_path: Path) -> None:
    from app.config import get_settings

    os.environ["BOOKWISE_DB_URL"] = f"sqlite:///{db_path}"
    get_settings.cache_clear()
    backend_root = Path(__file__).resolve().parents[2]
    alembic_cfg = Config(str(backend_root / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(backend_root / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    command.upgrade(alembic_cfg, "head")


def test_sqlite_persistence_with_migrations(tmp_path) -> None:
    db_path = tmp_path / "persist.db"
    _run_migrations(db_path)

    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False}, future=True)
    maker = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

    with maker() as db:
        db: Session
        book_repo = BookRepository(db)
        generation_repo = GenerationRepository(db)

        book_repo.create_or_update(
            work_id="OLPERSISTW",
            title="Persistence Book",
            authors="Author Name",
            description="A persistent book.",
            cover_url=None,
            subjects='["test"]',
        )

        pending = generation_repo.get_or_create("OLPERSISTW", GenerationSection.KEY_IDEAS)
        assert pending.status == GenerationStatus.PENDING

        claimed = generation_repo.claim_job(
            work_id="OLPERSISTW",
            section=GenerationSection.KEY_IDEAS,
            locked_by="worker-test",
            lease_seconds=100,
        )
        assert claimed

        completed_key = generation_repo.mark_completed(
            work_id="OLPERSISTW",
            section=GenerationSection.KEY_IDEAS,
            content='{"key_ideas":"- deterministic idea"}',
            prompt_name="key_ideas",
            prompt_version="test-v1",
            prompt_hash="abc123",
            idempotency_key="idem-123",
            input_fingerprint="finger-123",
            job_id="job-123",
            model="fake-model",
            tokens_prompt=10,
            tokens_completion=20,
            generation_time_ms=99,
        )
        assert completed_key.status == GenerationStatus.COMPLETED
        assert completed_key.prompt_name == "key_ideas"
        assert completed_key.prompt_version == "test-v1"
        assert completed_key.prompt_hash == "abc123"
        assert completed_key.idempotency_key == "idem-123"
        assert completed_key.input_fingerprint == "finger-123"

        critique_pending = generation_repo.get_or_create("OLPERSISTW", GenerationSection.CRITIQUE)
        assert critique_pending.status == GenerationStatus.PENDING

        assert generation_repo.claim_job(
            work_id="OLPERSISTW",
            section=GenerationSection.CRITIQUE,
            locked_by="worker-test",
            lease_seconds=100,
        )
        completed_critique = generation_repo.mark_completed(
            work_id="OLPERSISTW",
            section=GenerationSection.CRITIQUE,
            content='{"strengths":"x","weaknesses":"y","who_should_read":"z"}',
            prompt_name="critique",
            prompt_version="test-v1",
            prompt_hash="def456",
            idempotency_key="idem-456",
            input_fingerprint="finger-456",
            job_id="job-456",
            model="fake-model",
            tokens_prompt=11,
            tokens_completion=21,
            generation_time_ms=101,
        )
        assert completed_critique.status == GenerationStatus.COMPLETED
        assert completed_critique.prompt_name == "critique"
        assert completed_critique.prompt_version == "test-v1"
        assert completed_critique.prompt_hash == "def456"
