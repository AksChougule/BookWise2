from __future__ import annotations

import logging
from time import perf_counter

from app.clients.youtube_client import YouTubeClient
from app.repositories.youtube_repo import YouTubeRepository
from app.schemas.external_sections import YouTubeVideoOut, YouTubeVideosOut

logger = logging.getLogger(__name__)


class YouTubeService:
    def __init__(self, repo: YouTubeRepository, client: YouTubeClient):
        self.repo = repo
        self.client = client

    @staticmethod
    def _title_looks_english(title: str) -> bool:
        ascii_chars = sum(1 for ch in title if ord(ch) < 128)
        if not title:
            return False
        return (ascii_chars / max(len(title), 1)) >= 0.8

    @staticmethod
    def _normalize_views(value: str | int | None) -> int:
        if isinstance(value, int):
            return max(value, 0)
        if isinstance(value, str) and value.isdigit():
            return int(value)
        return 0

    @staticmethod
    def _extract_primary_author(authors_text: str | None) -> str:
        if not authors_text:
            return ""
        return authors_text.split(",", maxsplit=1)[0].strip()

    async def get_for_book(self, *, work_id: str, title: str, authors_text: str | None) -> YouTubeVideosOut:
        cached = self.repo.list_by_work_id(work_id)
        if cached:
            logger.info(
                "youtube_cache_hit",
                extra={
                    "event": "youtube_cache_hit",
                    "work_id": work_id,
                    "count": len(cached),
                },
            )
            return YouTubeVideosOut(
                work_id=work_id,
                source="cache",
                videos=[
                    YouTubeVideoOut(
                        video_id=row.video_id,
                        title=row.title,
                        channel=row.channel,
                        views=row.views,
                        published_at=row.published_at,
                        thumbnail=row.thumbnail,
                    )
                    for row in cached
                ],
            )

        author = self._extract_primary_author(authors_text)
        queries = [
            f"{author} {title} interview".strip(),
            f"{title} summary",
            f"{title} review",
        ]

        logger.info(
            "youtube_fetch_started",
            extra={
                "event": "youtube_fetch_started",
                "work_id": work_id,
                "query_count": len(queries),
            },
        )

        start = perf_counter()
        candidates: dict[str, dict] = {}

        for query_idx, query in enumerate(queries):
            items = await self.client.search_videos(query=query, max_results=10)
            for rank, item in enumerate(items):
                if not isinstance(item, dict):
                    continue
                item_id = item.get("id")
                if not isinstance(item_id, dict):
                    continue
                video_id = item_id.get("videoId")
                if not isinstance(video_id, str) or not video_id.strip():
                    continue

                snippet = item.get("snippet") if isinstance(item.get("snippet"), dict) else {}
                score = (query_idx * 100) + rank
                prev = candidates.get(video_id)
                if prev is None or score < prev["score"]:
                    candidates[video_id] = {"score": score, "snippet": snippet}

        details = await self.client.get_video_details(video_ids=list(candidates.keys()))
        ranked: list[dict] = []

        for video_id, candidate in candidates.items():
            detail = details.get(video_id, {})
            snippet = detail.get("snippet") if isinstance(detail.get("snippet"), dict) else candidate["snippet"]
            stats = detail.get("statistics") if isinstance(detail.get("statistics"), dict) else {}

            language = (snippet.get("defaultAudioLanguage") or snippet.get("defaultLanguage") or "").lower()
            title_text = str(snippet.get("title") or "")
            if language and not language.startswith("en"):
                continue
            if not language and not self._title_looks_english(title_text):
                continue

            channel = str(snippet.get("channelTitle") or "Unknown channel")
            thumbnail = None
            thumbnails = snippet.get("thumbnails") if isinstance(snippet.get("thumbnails"), dict) else {}
            for key in ("high", "medium", "default"):
                item = thumbnails.get(key)
                if isinstance(item, dict) and isinstance(item.get("url"), str):
                    thumbnail = item["url"]
                    break

            ranked.append(
                {
                    "video_id": video_id,
                    "title": title_text or "Untitled video",
                    "channel": channel,
                    "views": self._normalize_views(stats.get("viewCount")),
                    "published_at": self.client.parse_published_at(snippet.get("publishedAt")),
                    "thumbnail": thumbnail,
                    "score": candidate["score"],
                }
            )

        ranked.sort(key=lambda item: (-item["views"], item["score"], item["title"]))
        top4 = ranked[:4]

        persisted = self.repo.replace_for_work(work_id=work_id, videos=top4)

        logger.info(
            "youtube_fetch_completed",
            extra={
                "event": "youtube_fetch_completed",
                "work_id": work_id,
                "count": len(persisted),
                "duration_ms": int((perf_counter() - start) * 1000),
            },
        )

        return YouTubeVideosOut(
            work_id=work_id,
            source="api",
            videos=[
                YouTubeVideoOut(
                    video_id=row.video_id,
                    title=row.title,
                    channel=row.channel,
                    views=row.views,
                    published_at=row.published_at,
                    thumbnail=row.thumbnail,
                )
                for row in persisted
            ],
        )
