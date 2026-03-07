import asyncio

from app.schemas.books import SearchResponse
from app.services.search_service import SearchService
from app.utils.search_cache import SearchCache


class _FakeOpenLibraryClient:
    def __init__(self) -> None:
        self.calls = 0

    async def search_books(self, query: str, limit: int = 25) -> dict:
        self.calls += 1
        return {
            "docs": [
                {
                    "key": "/works/OL1W",
                    "title": f"{query} title",
                    "author_name": ["Author"],
                    "first_publish_year": 1954,
                    "cover_i": 123,
                }
            ]
        }


def test_search_cache_miss_then_hit() -> None:
    fake_client = _FakeOpenLibraryClient()
    cache = SearchCache[SearchResponse](ttl_seconds=24 * 60 * 60)
    service = SearchService(client=fake_client, cache=cache)

    first = asyncio.run(service.search("lord"))
    second = asyncio.run(service.search("lord"))

    assert first.count == 1
    assert second.count == 1
    assert fake_client.calls == 1


def test_search_cache_ttl_expiry() -> None:
    now = [100.0]

    def time_fn() -> float:
        return now[0]

    fake_client = _FakeOpenLibraryClient()
    cache = SearchCache[SearchResponse](ttl_seconds=2, time_fn=time_fn)
    service = SearchService(client=fake_client, cache=cache)

    asyncio.run(service.search("lord"))
    assert fake_client.calls == 1

    now[0] += 1
    asyncio.run(service.search("lord"))
    assert fake_client.calls == 1

    now[0] += 2
    asyncio.run(service.search("lord"))
    assert fake_client.calls == 2
