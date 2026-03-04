from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.clients.openlibrary_client import OpenLibraryClient
from app.repositories.book_repo import BookRepository
from app.schemas.books import BookOut


class BookService:
    def __init__(self, db: Session, client: OpenLibraryClient):
        self.db = db
        self.client = client
        self.book_repo = BookRepository(db)

    @staticmethod
    def _description_text(raw_description: str | dict | None) -> str | None:
        if isinstance(raw_description, str):
            return raw_description
        if isinstance(raw_description, dict):
            value = raw_description.get("value")
            if isinstance(value, str):
                return value
        return None

    @staticmethod
    def _cover_url(covers: list | None) -> str | None:
        if not isinstance(covers, list) or not covers:
            return None
        cover_id = covers[0]
        if isinstance(cover_id, int):
            return f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg"
        return None

    @staticmethod
    def _to_book_out(book) -> BookOut:
        subjects = []
        if book.subjects:
            try:
                parsed = json.loads(book.subjects)
                if isinstance(parsed, list):
                    subjects = [str(item) for item in parsed]
            except json.JSONDecodeError:
                subjects = []

        return BookOut(
            work_id=book.work_id,
            title=book.title,
            authors=book.authors,
            description=book.description,
            cover_url=book.cover_url,
            subjects=subjects,
            created_at=book.created_at,
            updated_at=book.updated_at,
        )

    async def get_book(self, work_id: str) -> BookOut:
        existing = self.book_repo.get_by_work_id(work_id)
        if existing:
            return self._to_book_out(existing)

        work = await self.client.get_work(work_id)
        title = work.get("title") or "Untitled"
        description = self._description_text(work.get("description"))
        subjects = work.get("subjects") if isinstance(work.get("subjects"), list) else []
        subjects_json = json.dumps(subjects)

        authors: list[str] = []
        for author_entry in work.get("authors", []):
            if not isinstance(author_entry, dict):
                continue
            author = author_entry.get("author")
            if not isinstance(author, dict):
                continue
            key = author.get("key")
            if isinstance(key, str):
                author_name = await self.client.get_author_name(key)
                if author_name:
                    authors.append(author_name)

        authors_text = ", ".join(dict.fromkeys(authors)) if authors else None

        book = self.book_repo.create_or_update(
            work_id=work_id,
            title=title,
            authors=authors_text,
            description=description,
            cover_url=self._cover_url(work.get("covers")),
            subjects=subjects_json,
        )
        return self._to_book_out(book)
