from app.clients.openlibrary_client import OpenLibraryClient
from app.schemas.books import SearchBookOut, SearchResponse


class SearchService:
    def __init__(self, client: OpenLibraryClient):
        self.client = client

    async def search(self, query: str) -> SearchResponse:
        payload = await self.client.search_books(query=query, limit=25)
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

            cover_i = doc.get("cover_i")
            cover_url = (
                f"https://covers.openlibrary.org/b/id/{cover_i}-M.jpg" if isinstance(cover_i, int) else None
            )

            results.append(
                SearchBookOut(
                    work_id=work_id,
                    title=title,
                    authors=authors,
                    cover_url=cover_url,
                )
            )

        return SearchResponse(query=query, count=len(results), results=results)
