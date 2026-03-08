import asyncio

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.repositories.explore_links_repo import ExploreLinksRepository
from app.services.explore_links_service import ExploreLinksService
from app.utils.db import Base


class _FakeOpenLibraryClient:
    def __init__(self) -> None:
        self.work_calls = 0
        self.author_calls = 0

    async def get_work(self, work_id: str) -> dict:
        self.work_calls += 1
        _ = work_id
        return {
            "authors": [
                {
                    "author": {
                        "key": "/authors/OL1A",
                    }
                }
            ]
        }

    async def get_author(self, author_key: str) -> dict:
        self.author_calls += 1
        _ = author_key
        return {
            "links": [
                {
                    "title": "Official Website",
                    "url": "https://author.example.com",
                }
            ]
        }


def _session_factory():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def test_explore_links_deterministic_generation_and_cache_reuse() -> None:
    maker = _session_factory()
    client = _FakeOpenLibraryClient()

    with maker() as db:
        service = ExploreLinksService(repo=ExploreLinksRepository(db), client=client)

        first = asyncio.run(service.get_for_book(work_id="OLEXPLOREW", title="Atomic Habits", authors_text="James Clear"))
        assert first.source == "resolved"
        assert first.amazon_url.startswith("https://www.amazon.com/s?k=Atomic+Habits+James+Clear")
        assert first.goodreads_url.startswith("https://www.goodreads.com/search?q=Atomic+Habits+James+Clear")
        assert first.author_website == "https://author.example.com"
        assert client.work_calls == 1
        assert client.author_calls == 1

        second = asyncio.run(service.get_for_book(work_id="OLEXPLOREW", title="Atomic Habits", authors_text="James Clear"))
        assert second.source == "cache"
        assert second.amazon_url == first.amazon_url
        assert second.goodreads_url == first.goodreads_url
        assert second.author_website == first.author_website
        assert client.work_calls == 1
        assert client.author_calls == 1
