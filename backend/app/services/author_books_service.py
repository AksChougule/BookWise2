from __future__ import annotations

import logging
from time import perf_counter

from app.clients.openlibrary_client import OpenLibraryClient
from app.schemas.external_sections import AuthorBookItemOut, AuthorBooksGroupOut, AuthorBooksOut

logger = logging.getLogger(__name__)


class AuthorBooksService:
    def __init__(self, client: OpenLibraryClient):
        self.client = client

    @staticmethod
    def _extract_primary_authors(authors_text: str | None) -> list[str]:
        if not authors_text:
            return []
        names = [item.strip() for item in authors_text.split(",")]
        return [name for name in names if name][:3]

    @staticmethod
    def _cover_url(doc: dict) -> str | None:
        cover_id = doc.get("cover_i")
        if isinstance(cover_id, int):
            return f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg"
        return None

    async def fetch_for_book(self, *, work_id: str, authors_text: str | None) -> AuthorBooksOut:
        authors = self._extract_primary_authors(authors_text)
        groups: list[AuthorBooksGroupOut] = []

        logger.info(
            "author_books_fetch_started",
            extra={
                "event": "author_books_fetch_started",
                "work_id": work_id,
                "author_count": len(authors),
            },
        )

        start = perf_counter()
        for author in authors:
            payload = await self.client.search_books_by_author(author=author, limit=18)
            docs = payload.get("docs", []) if isinstance(payload.get("docs"), list) else []

            books: list[AuthorBookItemOut] = []
            seen_work_ids: set[str] = set()

            for doc in docs:
                if not isinstance(doc, dict):
                    continue
                work_key = doc.get("key")
                if not isinstance(work_key, str) or not work_key.startswith("/works/"):
                    continue
                candidate_work_id = work_key.rsplit("/", maxsplit=1)[-1]
                if candidate_work_id == work_id or candidate_work_id in seen_work_ids:
                    continue
                seen_work_ids.add(candidate_work_id)

                author_names = doc.get("author_name")
                first_author = None
                if isinstance(author_names, list):
                    for name in author_names:
                        if isinstance(name, str) and name.strip():
                            first_author = name.strip()
                            break

                year = doc.get("first_publish_year")
                books.append(
                    AuthorBookItemOut(
                        work_id=candidate_work_id,
                        title=str(doc.get("title") or "Untitled"),
                        authors=first_author,
                        first_publish_year=year if isinstance(year, int) else None,
                        cover_url=self._cover_url(doc),
                    )
                )

                if len(books) >= 6:
                    break

            groups.append(AuthorBooksGroupOut(author=author, books=books))

        logger.info(
            "author_books_fetch_completed",
            extra={
                "event": "author_books_fetch_completed",
                "work_id": work_id,
                "groups": len(groups),
                "duration_ms": int((perf_counter() - start) * 1000),
            },
        )
        return AuthorBooksOut(work_id=work_id, groups=groups)
