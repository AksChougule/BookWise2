import asyncio

from app.services.author_books_service import AuthorBooksService


class _FakeOpenLibraryClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int]] = []

    async def search_books_by_author(self, author: str, limit: int = 18) -> dict:
        self.calls.append((author, limit))
        return {
            "docs": [
                {
                    "key": "/works/OL2W",
                    "title": f"{author} Book One",
                    "author_name": [author],
                    "first_publish_year": 2001,
                    "cover_i": 11,
                    "language": ["/languages/eng"],
                },
                {
                    "key": "/works/OL3W",
                    "title": f"{author} Book Two",
                    "author_name": [author],
                    "first_publish_year": 2005,
                    "cover_i": 12,
                    "language": ["/languages/fre"],
                },
            ]
        }


def test_author_books_groups_first_three_authors_and_limits_books() -> None:
    client = _FakeOpenLibraryClient()
    service = AuthorBooksService(client=client)

    result = asyncio.run(
        service.fetch_for_book(
            work_id="OL1W",
            authors_text="Author A, Author B, Author C, Author D",
        )
    )

    assert len(result.groups) == 3
    assert [group.author for group in result.groups] == ["Author A", "Author B", "Author C"]
    assert all(len(group.books) <= 6 for group in result.groups)
    assert all(len(group.books) == 1 for group in result.groups)
    assert len(client.calls) == 3
    assert result.groups[0].books[0].cover_url == "https://covers.openlibrary.org/b/id/11-M.jpg"
