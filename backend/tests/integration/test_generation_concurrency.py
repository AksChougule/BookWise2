import asyncio

from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.clients.openlibrary_client import OpenLibraryClient
from app.main import app
from app.models.generation import Generation, GenerationSection
from app.providers import reset_provider_factory, set_provider_factory
from app.providers.fake_provider import FakeLLMProvider
from app.schemas.generations import KeyIdeasOut
from app.services import generation_service as generation_service_module
from app.utils.db import Base, get_db


WORK_ID = "OLCONCURRENCYW"


def _session_factory(db_path: str):
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False}, future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


async def _wait_until_completed(client: AsyncClient, work_id: str, retries: int = 40, sleep_s: float = 0.05) -> KeyIdeasOut:
    for _ in range(retries):
        res = await client.get(f"/api/books/{work_id}/key-ideas")
        assert res.status_code == 200
        parsed = KeyIdeasOut.model_validate(res.json())
        if parsed.status == "completed":
            return parsed
        await asyncio.sleep(sleep_s)
    raise AssertionError("key ideas did not reach completed state in time")


def test_generation_concurrency_single_llm_call(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "concurrency.db"
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
            "title": "Concurrency Test Book",
            "description": "Test description",
            "subjects": ["Testing"],
            "covers": [123],
            "authors": [{"author": {"key": "/authors/OL1A"}}],
            "key": f"/works/{work_id}",
        }

    async def fake_get_author_name(self, author_key: str):
        _ = (self, author_key)
        return "Test Author"

    monkeypatch.setattr(OpenLibraryClient, "get_work", fake_get_work)
    monkeypatch.setattr(OpenLibraryClient, "get_author_name", fake_get_author_name)

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(generation_service_module, "SessionLocal", session_factory)
    FakeLLMProvider.reset_call_count()
    set_provider_factory(lambda: FakeLLMProvider(model="fake-concurrency"))

    async def run() -> None:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            requests = [client.get(f"/api/books/{WORK_ID}/key-ideas") for _ in range(10)]
            initial_responses = await asyncio.gather(*requests)
            for resp in initial_responses:
                assert resp.status_code == 200

            completions = await asyncio.gather(*[_wait_until_completed(client, WORK_ID) for _ in range(10)])
            for item in completions:
                assert item.status == "completed"
                assert item.section == "key_ideas"

    try:
        asyncio.run(run())

        with session_factory() as db:
            stmt = select(Generation).where(
                Generation.work_id == WORK_ID,
                Generation.section == GenerationSection.KEY_IDEAS,
            )
            rows = list(db.scalars(stmt))
            assert len(rows) == 1
            assert rows[0].section == GenerationSection.KEY_IDEAS

        assert FakeLLMProvider.call_count == 1
    finally:
        app.dependency_overrides.clear()
        reset_provider_factory()
