import asyncio
from collections import defaultdict

_lock_store: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)


def get_lock(key: str) -> asyncio.Lock:
    return _lock_store[key]
