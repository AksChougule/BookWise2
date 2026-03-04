from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.book import Book


class BookRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_work_id(self, work_id: str) -> Book | None:
        stmt = select(Book).where(Book.work_id == work_id)
        return self.db.scalar(stmt)

    def create_or_update(
        self,
        *,
        work_id: str,
        title: str,
        authors: str | None,
        description: str | None,
        cover_url: str | None,
        subjects: str | None,
    ) -> Book:
        book = self.get_by_work_id(work_id)
        if book is None:
            book = Book(
                work_id=work_id,
                title=title,
                authors=authors,
                description=description,
                cover_url=cover_url,
                subjects=subjects,
            )
            self.db.add(book)
        else:
            book.title = title
            book.authors = authors
            book.description = description
            book.cover_url = cover_url
            book.subjects = subjects

        self.db.commit()
        self.db.refresh(book)
        return book
