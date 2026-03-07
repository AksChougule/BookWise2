import asyncio

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.book import Book
from app.providers import get_provider, reset_provider_factory, set_provider_factory
from app.providers.fake_provider import FakeLLMProvider
from app.services.generation_service import GenerationService
from app.utils.db import Base


def _session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    return maker()


def test_fake_provider_returns_deterministic_structured_results() -> None:
    FakeLLMProvider.reset_call_count()
    provider = FakeLLMProvider(model="fake-test")

    key_ideas = asyncio.run(
        provider.generate_structured(
            prompt="irrelevant",
            schema_name="key_ideas_response",
            schema={},
            max_output_tokens=100,
        )
    )
    critique = asyncio.run(
        provider.generate_structured(
            prompt="irrelevant",
            schema_name="critique_response",
            schema={},
            max_output_tokens=100,
        )
    )

    assert "Deterministic idea 1" in key_ideas.data["key_ideas"]
    assert "Clear structure" in critique.data["strengths"]
    assert FakeLLMProvider.call_count == 2
    assert provider.number_of_calls == 2


def test_provider_factory_override_and_service_injection() -> None:
    try:
        set_provider_factory(lambda: FakeLLMProvider(model="factory-fake"))
        provider = get_provider()
        assert isinstance(provider, FakeLLMProvider)
        assert provider.model == "factory-fake"

        db = _session()
        try:
            db.add(Book(work_id="OL1W", title="Test Book", authors="A"))
            db.commit()
            service = GenerationService(db, provider=provider)
            assert service.provider is provider
        finally:
            db.close()
    finally:
        reset_provider_factory()
