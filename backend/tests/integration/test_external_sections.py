import asyncio

from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.clients.openlibrary_client import OpenLibraryClient
from app.clients.youtube_client import YouTubeClient
from app.main import app
from app.schemas.external_sections import AuthorBooksOut, ExploreLinksOut, YouTubeVideosOut
from app.utils.db import Base, get_db


def _session_factory(db_path: str):
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False}, future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def test_external_sections_endpoints(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "external_sections.db"
    session_factory = _session_factory(str(db_path))

    def override_get_db():
        db: Session = session_factory()
        try:
            yield db
        finally:
            db.close()

    async def fake_get_work(self, work_id: str):
        _ = self
        return {
            "title": "The Lord of the Rings",
            "description": "Epic fantasy trilogy.",
            "subjects": ["Fantasy"],
            "covers": [123],
            "authors": [{"author": {"key": "/authors/OL26320A"}}],
            "key": f"/works/{work_id}",
        }

    async def fake_get_author_name(self, author_key: str):
        _ = (self, author_key)
        return "J.R.R. Tolkien"

    async def fake_search_books_by_author(self, author: str, limit: int = 18):
        _ = (self, author, limit)
        return {
            "docs": [
                {
                    "key": "/works/OL27479W",
                    "title": "The Two Towers",
                    "author_name": ["J.R.R. Tolkien"],
                    "first_publish_year": 1954,
                    "cover_i": 321,
                }
            ]
        }

    async def fake_search_videos(self, *, query: str, max_results: int = 8):
        _ = (self, query, max_results)
        return [
            {
                "id": {"videoId": "abc123"},
                "snippet": {
                    "title": "Tolkien Interview",
                    "channelTitle": "Book Channel",
                    "publishedAt": "2020-01-01T00:00:00Z",
                    "defaultLanguage": "en",
                    "thumbnails": {"high": {"url": "https://img.youtube/abc123.jpg"}},
                },
            }
        ]

    async def fake_get_video_details(self, *, video_ids: list[str]):
        _ = self
        return {
            video_id: {
                "snippet": {
                    "title": "Tolkien Interview",
                    "channelTitle": "Book Channel",
                    "publishedAt": "2020-01-01T00:00:00Z",
                    "defaultLanguage": "en",
                    "thumbnails": {"high": {"url": "https://img.youtube/abc123.jpg"}},
                },
                "statistics": {"viewCount": "12345"},
            }
            for video_id in video_ids
        }

    async def fake_get_author(self, author_key: str):
        _ = (self, author_key)
        return {
            "links": [
                {
                    "title": "Official Website",
                    "url": "https://tolkienestate.example.com",
                }
            ]
        }

    monkeypatch.setattr(OpenLibraryClient, "get_work", fake_get_work)
    monkeypatch.setattr(OpenLibraryClient, "get_author_name", fake_get_author_name)
    monkeypatch.setattr(OpenLibraryClient, "search_books_by_author", fake_search_books_by_author)
    monkeypatch.setattr(OpenLibraryClient, "get_author", fake_get_author)
    monkeypatch.setattr(YouTubeClient, "search_videos", fake_search_videos)
    monkeypatch.setattr(YouTubeClient, "get_video_details", fake_get_video_details)

    app.dependency_overrides[get_db] = override_get_db

    async def run() -> None:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            other_books_res = await client.get("/api/books/OL27448W/other-books")
            assert other_books_res.status_code == 200
            parsed_other = AuthorBooksOut.model_validate(other_books_res.json())
            assert parsed_other.work_id == "OL27448W"
            assert parsed_other.groups

            youtube_res = await client.get("/api/books/OL27448W/youtube-videos")
            assert youtube_res.status_code == 200
            parsed_youtube = YouTubeVideosOut.model_validate(youtube_res.json())
            assert parsed_youtube.work_id == "OL27448W"
            assert parsed_youtube.videos

            youtube_cached_res = await client.get("/api/books/OL27448W/youtube-videos")
            assert youtube_cached_res.status_code == 200
            parsed_youtube_cached = YouTubeVideosOut.model_validate(youtube_cached_res.json())
            assert parsed_youtube_cached.source == "cache"

            explore_res = await client.get("/api/books/OL27448W/explore-more")
            assert explore_res.status_code == 200
            parsed_explore = ExploreLinksOut.model_validate(explore_res.json())
            assert parsed_explore.work_id == "OL27448W"
            assert parsed_explore.amazon_url
            assert parsed_explore.goodreads_url

            explore_cached_res = await client.get("/api/books/OL27448W/explore-more")
            assert explore_cached_res.status_code == 200
            parsed_explore_cached = ExploreLinksOut.model_validate(explore_cached_res.json())
            assert parsed_explore_cached.source == "cache"

    try:
        asyncio.run(run())
    finally:
        app.dependency_overrides.clear()
