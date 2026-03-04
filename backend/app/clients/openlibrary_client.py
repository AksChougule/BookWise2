from __future__ import annotations

from typing import Any

import httpx

from app.config import get_settings


class OpenLibraryClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url = self.settings.openlibrary_base_url.rstrip("/")

    async def _get_json(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()

    async def search_books(self, query: str, limit: int = 25) -> dict[str, Any]:
        return await self._get_json("/search.json", params={"q": query, "limit": limit})

    async def get_work(self, work_id: str) -> dict[str, Any]:
        return await self._get_json(f"/works/{work_id}.json")

    async def get_author_name(self, author_key: str) -> str | None:
        try:
            author_data = await self._get_json(f"{author_key}.json")
        except httpx.HTTPError:
            return None
        name = author_data.get("name")
        return name if isinstance(name, str) and name.strip() else None
