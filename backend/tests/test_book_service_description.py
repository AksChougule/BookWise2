from app.services.book_service import BookService


def test_description_strips_contains_section_with_delimiter() -> None:
    raw = (
        "Originally published from 1954 through 1956.\n"
        "---------- **Contains**\n"
        "- [The Fellowship of the Ring][1]\n"
        "- [The Two Towers][2]\n"
        "[1]: https://openlibrary.org/works/OL14933414W"
    )

    result = BookService._description_text(raw)

    assert result == "Originally published from 1954 through 1956."


def test_description_strips_inline_contains_section() -> None:
    raw = (
        "A classic fantasy trilogy. **Contains** - [The Fellowship of the Ring][1] "
        "- [The Two Towers][2]"
    )

    result = BookService._description_text(raw)

    assert result == "A classic fantasy trilogy."


def test_description_keeps_regular_text_when_no_contains_section() -> None:
    raw = "A classic fantasy trilogy with rich worldbuilding."

    result = BookService._description_text(raw)

    assert result == raw
