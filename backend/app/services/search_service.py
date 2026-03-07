import logging
from time import perf_counter

from app.clients.openlibrary_client import OpenLibraryClient
from app.schemas.books import SearchBookOut, SearchResponse
from app.utils.search_cache import SearchCache

logger = logging.getLogger(__name__)

_search_cache: SearchCache[SearchResponse] = SearchCache(ttl_seconds=24 * 60 * 60)


class SearchService:
    def __init__(self, client: OpenLibraryClient, cache: SearchCache[SearchResponse] | None = None):
        self.client = client
        self.cache = cache or _search_cache

    async def search(self, query: str) -> SearchResponse:
        normalized_query = query.strip()
        start = perf_counter()
        cached = self.cache.get(normalized_query)
        if cached is not None:
            latency_ms = int((perf_counter() - start) * 1000)
            logger.info(
                "cache_hit",
                extra={
                    "event": "cache_hit",
                    "cache": "search",
                    "query": normalized_query,
                    "count": cached.count,
                    "latency_ms": latency_ms,
                },
            )
            return cached.model_copy(deep=True)

        logger.info(
            "cache_miss",
            extra={
                "event": "cache_miss",
                "cache": "search",
                "query": normalized_query,
            },
        )
        payload = await self.client.search_books(query=normalized_query, limit=25)
        response = self._from_payload(query=normalized_query, payload=payload)
        self.cache.set(normalized_query, response)
        latency_ms = int((perf_counter() - start) * 1000)
        logger.info(
            "search_completed",
            extra={
                "event": "search_completed",
                "query": normalized_query,
                "count": response.count,
                "latency_ms": latency_ms,
            },
        )
        return response

    @staticmethod
    def _from_payload(*, query: str, payload: dict) -> SearchResponse:
        docs = payload.get("docs", [])
        results: list[SearchBookOut] = []
        for doc in docs[:25]:
            work_key = doc.get("key")
            if not isinstance(work_key, str) or not work_key.startswith("/works/"):
                continue
            work_id = work_key.rsplit("/", maxsplit=1)[-1]
            title = doc.get("title") or "Untitled"

            author_names = doc.get("author_name") or []
            authors = ", ".join([a for a in author_names if isinstance(a, str)]) or None
            first_publish_year = doc.get("first_publish_year")
            if not isinstance(first_publish_year, int):
                first_publish_year = None

            cover_i = doc.get("cover_i")
            cover_url = (
                f"https://covers.openlibrary.org/b/id/{cover_i}-M.jpg" if isinstance(cover_i, int) else None
            )

            results.append(
                SearchBookOut(
                    work_id=work_id,
                    title=title,
                    authors=authors,
                    first_publish_year=first_publish_year,
                    cover_url=cover_url,
                )
            )

        return SearchResponse(query=query, count=len(results), results=results)
