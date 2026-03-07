from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from app.config import get_settings


class YouTubeClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = settings.youtube_api_key
        self.base_url = settings.youtube_base_url.rstrip("/")

    async def _get_json(self, path: str, *, params: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()

    async def search_videos(self, *, query: str, max_results: int = 8) -> list[dict[str, Any]]:
        if not self.api_key:
            raise RuntimeError("YOUTUBE_API_KEY is not configured")

        payload = await self._get_json(
            "/search",
            params={
                "key": self.api_key,
                "part": "snippet",
                "q": query,
                "type": "video",
                "maxResults": max_results,
                "relevanceLanguage": "en",
                "regionCode": "US",
                "safeSearch": "moderate",
            },
        )
        return payload.get("items", []) if isinstance(payload.get("items"), list) else []

    async def get_video_details(self, *, video_ids: list[str]) -> dict[str, dict[str, Any]]:
        if not video_ids:
            return {}
        if not self.api_key:
            raise RuntimeError("YOUTUBE_API_KEY is not configured")

        payload = await self._get_json(
            "/videos",
            params={
                "key": self.api_key,
                "part": "snippet,statistics,contentDetails",
                "id": ",".join(video_ids),
                "maxResults": len(video_ids),
            },
        )
        result: dict[str, dict[str, Any]] = {}
        items = payload.get("items", []) if isinstance(payload.get("items"), list) else []
        for item in items:
            if not isinstance(item, dict):
                continue
            video_id = item.get("id")
            if isinstance(video_id, str):
                result[video_id] = item
        return result

    @staticmethod
    def parse_published_at(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
