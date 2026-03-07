from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from threading import Lock
import time
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(slots=True)
class _CacheEntry(Generic[T]):
    value: T
    expires_at: float


class SearchCache(Generic[T]):
    def __init__(self, ttl_seconds: int = 24 * 60 * 60, time_fn: Callable[[], float] | None = None):
        self.ttl_seconds = ttl_seconds
        self._time_fn = time_fn or time.monotonic
        self._lock = Lock()
        self._items: dict[str, _CacheEntry[T]] = {}

    @staticmethod
    def _key(query: str) -> str:
        return query.strip().lower()

    def get(self, query: str) -> T | None:
        key = self._key(query)
        now = self._time_fn()
        with self._lock:
            item = self._items.get(key)
            if item is None:
                return None
            if item.expires_at <= now:
                self._items.pop(key, None)
                return None
            return item.value

    def set(self, query: str, value: T) -> None:
        key = self._key(query)
        with self._lock:
            self._items[key] = _CacheEntry(value=value, expires_at=self._time_fn() + self.ttl_seconds)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()
