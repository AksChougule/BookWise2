import asyncio

from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.clients.openlibrary_client import OpenLibraryClient
from app.main import app
from app.models.generation import Generation, GenerationSection, GenerationStatus
from app.providers import reset_provider_factory, set_provider_factory
from app.providers.fake_provider import FakeLLMProvider
from app.schemas.generations import SummaryOut
from app.services import generation_service as generation_service_module
from app.utils.db import Base, get_db


def _session_factory(db_path: str):
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False}, future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def test_summary_uses_openlibrary_description_when_available(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "summary_openlibrary.db"
    session_factory = _session_factory(str(db_path))

    def override_get_db():
        db: Session = session_factory()
        try:
            yield db
        finally:
            db.close()

    async def fake_get_work(self, work_id: str):
        _ = self
        return {
            "title": "Book",
            "description": "This is a long enough summary from Open Library to be considered usable for rendering.",
            "subjects": [],
            "covers": [123],
            "authors": [{"author": {"key": "/authors/OL1A"}}],
            "key": f"/works/{work_id}",
        }

    async def fake_get_author_name(self, author_key: str):
        _ = (self, author_key)
        return "Author"

    monkeypatch.setattr(OpenLibraryClient, "get_work", fake_get_work)
    monkeypatch.setattr(OpenLibraryClient, "get_author_name", fake_get_author_name)

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(generation_service_module, "SessionLocal", session_factory)
    FakeLLMProvider.reset_call_count()
    set_provider_factory(lambda: FakeLLMProvider(model="fake-summary"))

    async def run() -> None:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/api/books/OLSUMOPEN/summary")
            assert res.status_code == 200
            payload = SummaryOut.model_validate(res.json())
            assert payload.source == "openlibrary"
            assert payload.status == "completed"
            assert payload.summary is not None

    try:
        asyncio.run(run())
        assert FakeLLMProvider.call_count == 0
    finally:
        app.dependency_overrides.clear()
        reset_provider_factory()


def test_summary_falls_back_to_llm_and_persists_generation(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "summary_llm.db"
    session_factory = _session_factory(str(db_path))

    def override_get_db():
        db: Session = session_factory()
        try:
            yield db
        finally:
            db.close()

    async def fake_get_work(self, work_id: str):
        _ = self
        return {
            "title": "Book",
            "description": None,
            "subjects": [],
            "covers": [123],
            "authors": [{"author": {"key": "/authors/OL1A"}}],
            "key": f"/works/{work_id}",
        }

    async def fake_get_author_name(self, author_key: str):
        _ = (self, author_key)
        return "Author"

    monkeypatch.setattr(OpenLibraryClient, "get_work", fake_get_work)
    monkeypatch.setattr(OpenLibraryClient, "get_author_name", fake_get_author_name)

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(generation_service_module, "SessionLocal", session_factory)
    FakeLLMProvider.reset_call_count()
    set_provider_factory(lambda: FakeLLMProvider(model="fake-summary"))

    async def run() -> None:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/api/books/OLSUMLLM/summary")
            assert res.status_code == 200
            payload = SummaryOut.model_validate(res.json())
            assert payload.source == "llm"
            assert payload.status == "completed"
            assert payload.summary

    try:
        asyncio.run(run())
        assert FakeLLMProvider.call_count == 1

        with session_factory() as db:
            stmt = select(Generation).where(
                Generation.work_id == "OLSUMLLM",
                Generation.section == GenerationSection.SUMMARY_LLM,
            )
            row = db.scalar(stmt)
            assert row is not None
            assert row.status == GenerationStatus.COMPLETED
            assert row.prompt_name == "summary"
            assert row.prompt_hash
            assert row.prompt_version
    finally:
        app.dependency_overrides.clear()
        reset_provider_factory()
