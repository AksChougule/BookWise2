from __future__ import annotations

import logging
from time import perf_counter
from urllib.parse import quote_plus, urlparse

from app.clients.openlibrary_client import OpenLibraryClient
from app.repositories.explore_links_repo import ExploreLinksRepository
from app.schemas.external_sections import ExploreLinksOut

logger = logging.getLogger(__name__)


class ExploreLinksService:
    _UNTRUSTED_DOMAINS = {
        "openlibrary.org",
        "amazon.com",
        "goodreads.com",
        "wikipedia.org",
        "twitter.com",
        "x.com",
        "facebook.com",
        "instagram.com",
        "youtube.com",
    }

    def __init__(self, repo: ExploreLinksRepository, client: OpenLibraryClient):
        self.repo = repo
        self.client = client

    @staticmethod
    def _primary_author(authors_text: str | None) -> str:
        if not authors_text:
            return ""
        return authors_text.split(",", maxsplit=1)[0].strip()

    @classmethod
    def _domain_is_trusted(cls, url: str) -> bool:
        parsed = urlparse(url)
        host = (parsed.netloc or "").lower()
        if not host:
            return False
        host = host.removeprefix("www.")
        return not any(host == domain or host.endswith(f".{domain}") for domain in cls._UNTRUSTED_DOMAINS)

    @classmethod
    def _is_confident_author_link(cls, *, title: str | None, url: str | None) -> bool:
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            return False
        if not cls._domain_is_trusted(url):
            return False

        if isinstance(title, str):
            normalized_title = title.strip().lower()
            if "official" in normalized_title and "website" in normalized_title:
                return True
            if "official" in normalized_title and "site" in normalized_title:
                return True

        return False

    async def _resolve_author_website(self, *, work_id: str) -> str | None:
        work = await self.client.get_work(work_id)
        author_entries = work.get("authors") if isinstance(work.get("authors"), list) else []
        if not author_entries:
            return None

        first = author_entries[0]
        if not isinstance(first, dict):
            return None
        author_ref = first.get("author") if isinstance(first.get("author"), dict) else {}
        author_key = author_ref.get("key")
        if not isinstance(author_key, str) or not author_key.startswith("/authors/"):
            return None

        author = await self.client.get_author(author_key)
        links = author.get("links") if isinstance(author.get("links"), list) else []
        for link in links:
            if not isinstance(link, dict):
                continue
            if self._is_confident_author_link(title=link.get("title"), url=link.get("url")):
                return str(link["url"])

        website = author.get("website")
        if isinstance(website, str) and self._is_confident_author_link(title="official website", url=website):
            return website

        return None

    async def get_for_book(self, *, work_id: str, title: str, authors_text: str | None) -> ExploreLinksOut:
        cached = self.repo.get_by_work_id(work_id)
        if cached:
            logger.info(
                "explore_links_cache_hit",
                extra={
                    "event": "explore_links_cache_hit",
                    "work_id": work_id,
                },
            )
            return ExploreLinksOut(
                work_id=work_id,
                source="cache",
                amazon_url=cached.amazon_url,
                goodreads_url=cached.goodreads_url,
                author_website=cached.author_website,
            )

        logger.info(
            "explore_links_resolve_started",
            extra={
                "event": "explore_links_resolve_started",
                "work_id": work_id,
            },
        )
        start = perf_counter()

        author = self._primary_author(authors_text)
        query = " ".join(part for part in [title.strip(), author] if part)
        amazon_url = f"https://www.amazon.com/s?k={quote_plus(query)}"
        goodreads_url = f"https://www.goodreads.com/search?q={quote_plus(query)}"
        author_website = await self._resolve_author_website(work_id=work_id)

        row = self.repo.create_or_update(
            work_id=work_id,
            amazon_url=amazon_url,
            goodreads_url=goodreads_url,
            author_website=author_website,
        )

        logger.info(
            "explore_links_resolve_completed",
            extra={
                "event": "explore_links_resolve_completed",
                "work_id": work_id,
                "duration_ms": int((perf_counter() - start) * 1000),
                "author_website_included": bool(author_website),
            },
        )

        return ExploreLinksOut(
            work_id=work_id,
            source="resolved",
            amazon_url=row.amazon_url,
            goodreads_url=row.goodreads_url,
            author_website=row.author_website,
        )
