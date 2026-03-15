import asyncio
from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.repositories.youtube_repo import YouTubeRepository
from app.services.youtube_service import YouTubeService
from app.utils.db import Base


class _FakeYouTubeClient:
    def __init__(self) -> None:
        self.api_key = "test-key"
        self.search_calls = 0
        self.detail_calls = 0

    async def search_videos(self, *, query: str, max_results: int = 8) -> list[dict]:
        _ = max_results
        self.search_calls += 1
        if "interview" in query:
            return [
                {
                    "id": {"videoId": "vid1"},
                    "snippet": {
                        "title": "Book Interview in English",
                        "channelTitle": "Channel A",
                        "publishedAt": "2024-01-01T00:00:00Z",
                        "defaultLanguage": "en",
                        "thumbnails": {"high": {"url": "https://img/1.jpg"}},
                    },
                }
            ]
        if "summary" in query:
            return [
                {
                    "id": {"videoId": "vid2"},
                    "snippet": {
                        "title": "Book Summary",
                        "channelTitle": "Channel B",
                        "publishedAt": "2023-01-01T00:00:00Z",
                        "defaultLanguage": "en",
                        "thumbnails": {"high": {"url": "https://img/2.jpg"}},
                    },
                }
            ]
        return [
            {
                "id": {"videoId": "vid3"},
                "snippet": {
                    "title": "Book Review",
                    "channelTitle": "Channel C",
                    "publishedAt": "2022-01-01T00:00:00Z",
                    "defaultLanguage": "en",
                    "thumbnails": {"high": {"url": "https://img/3.jpg"}},
                },
            }
        ]

    async def get_video_details(self, *, video_ids: list[str]) -> dict[str, dict]:
        self.detail_calls += 1
        data = {
            "vid1": {
                "snippet": {
                    "title": "Book Interview in English",
                    "channelTitle": "Channel A",
                    "publishedAt": "2024-01-01T00:00:00Z",
                    "defaultLanguage": "en",
                    "thumbnails": {"high": {"url": "https://img/1.jpg"}},
                },
                "statistics": {"viewCount": "5000"},
                "contentDetails": {"duration": "PT18M2S"},
            },
            "vid2": {
                "snippet": {
                    "title": "Book Summary",
                    "channelTitle": "Channel B",
                    "publishedAt": "2023-01-01T00:00:00Z",
                    "defaultLanguage": "en",
                    "thumbnails": {"high": {"url": "https://img/2.jpg"}},
                },
                "statistics": {"viewCount": "9000"},
                "contentDetails": {"duration": "PT12M10S"},
            },
            "vid3": {
                "snippet": {
                    "title": "Book Review",
                    "channelTitle": "Channel C",
                    "publishedAt": "2022-01-01T00:00:00Z",
                    "defaultLanguage": "en",
                    "thumbnails": {"high": {"url": "https://img/3.jpg"}},
                },
                "statistics": {"viewCount": "2000"},
                "contentDetails": {"duration": "PT16M0S"},
            },
        }
        return {video_id: data[video_id] for video_id in video_ids if video_id in data}

    @staticmethod
    def parse_published_at(value: str | None) -> datetime | None:
        if not value:
            return None
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def _session_factory():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def test_youtube_service_persists_then_reuses_cache() -> None:
    maker = _session_factory()
    client = _FakeYouTubeClient()

    with maker() as db:
        service = YouTubeService(repo=YouTubeRepository(db), client=client)

        first = asyncio.run(service.get_for_book(work_id="OLYT1W", title="Book", authors_text="Author"))
        assert first.source == "api"
        assert len(first.videos) == 2
        assert [video.video_id for video in first.videos] == ["vid1", "vid3"]
        assert client.search_calls == 3
        assert client.detail_calls == 1

        second = asyncio.run(service.get_for_book(work_id="OLYT1W", title="Book", authors_text="Author"))
        assert second.source == "cache"
        assert len(second.videos) == 2
        assert client.search_calls == 3
        assert client.detail_calls == 1


def test_youtube_service_returns_empty_when_key_missing() -> None:
    maker = _session_factory()
    client = _FakeYouTubeClient()
    client.api_key = None

    with maker() as db:
        service = YouTubeService(repo=YouTubeRepository(db), client=client)
        result = asyncio.run(service.get_for_book(work_id="OLYT2W", title="Book", authors_text="Author"))
        assert result.source == "disabled"
        assert result.videos == []
        assert client.search_calls == 0
        assert client.detail_calls == 0
