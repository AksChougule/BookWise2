import asyncio
import json
from pathlib import Path

import yaml
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.clients.openlibrary_client import OpenLibraryClient
from app.main import app
from app.providers import reset_provider_factory, set_provider_factory
from app.providers.fake_provider import FakeLLMProvider
from app.schemas.books import BookOut, SearchResponse
from app.schemas.generations import CritiqueOut, KeyIdeasOut
from app.utils.db import Base, get_db


def _session_factory(db_path: Path):
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False}, future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def test_api_contracts(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "contract.db"
    session_factory = _session_factory(db_path)

    def override_get_db():
        db: Session = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    set_provider_factory(lambda: FakeLLMProvider(model="fake-contract"))

    async def fake_search_books(self, query: str, limit: int = 25):
        _ = (self, query, limit)
        return {
            "docs": [
                {
                    "key": "/works/OL27448W",
                    "title": "The Lord of the Rings",
                    "author_name": ["J.R.R. Tolkien"],
                    "first_publish_year": 1954,
                    "cover_i": 123,
                }
            ]
        }

    async def fake_get_work(self, work_id: str):
        _ = self
        return {
            "title": "The Lord of the Rings",
            "description": (
                "Epic fantasy trilogy. ---------- **Contains** - [The Fellowship of the Ring][1]"
            ),
            "subjects": ["Fantasy"],
            "covers": [123],
            "authors": [{"author": {"key": "/authors/OL26320A"}}],
            "key": f"/works/{work_id}",
        }

    async def fake_get_author_name(self, author_key: str):
        _ = (self, author_key)
        return "J.R.R. Tolkien"

    monkeypatch.setattr(OpenLibraryClient, "search_books", fake_search_books)
    monkeypatch.setattr(OpenLibraryClient, "get_work", fake_get_work)
    monkeypatch.setattr(OpenLibraryClient, "get_author_name", fake_get_author_name)

    from app.config import get_settings

    settings = get_settings()
    curated_path = tmp_path / "curated_books.yml"
    curated_path.write_text(
        yaml.safe_dump([{"work_id": "OL27448W", "title": "The Lord of the Rings", "authors": "J.R.R. Tolkien"}]),
        encoding="utf-8",
    )
    monkeypatch.setattr(settings, "curated_books_path", curated_path)

    async def run() -> None:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            search_res = await client.get("/api/search", params={"q": "lord"})
            assert search_res.status_code == 200
            parsed_search = SearchResponse.model_validate(search_res.json())
            assert parsed_search.results[0].first_publish_year == 1954

            book_res = await client.get("/api/books/OL27448W")
            assert book_res.status_code == 200
            parsed_book = BookOut.model_validate(book_res.json())
            assert parsed_book.description == "Epic fantasy trilogy."

            key_res = await client.get("/api/books/OL27448W/key-ideas")
            assert key_res.status_code == 200
            parsed_key = KeyIdeasOut.model_validate(key_res.json())
            assert parsed_key.work_id == "OL27448W"
            assert parsed_key.section == "key_ideas"
            assert parsed_key.status in {"completed", "generating", "pending", "failed"}

            critique_res = await client.get("/api/books/OL27448W/critique")
            assert critique_res.status_code == 200
            parsed_critique = CritiqueOut.model_validate(critique_res.json())
            assert parsed_critique.work_id == "OL27448W"
            assert parsed_critique.section == "critique"

            surprise_res = await client.get("/api/surprise")
            assert surprise_res.status_code == 200
            payload = surprise_res.json()
            assert isinstance(payload.get("work_id"), str)
            assert "title" in payload
            assert "authors" in payload

    try:
        asyncio.run(run())
    finally:
        app.dependency_overrides.clear()
        reset_provider_factory()
