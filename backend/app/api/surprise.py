import random
from typing import Any

import yaml
from fastapi import APIRouter, HTTPException

from app.config import get_settings

router = APIRouter()


@router.get("/surprise")
async def surprise_me() -> dict[str, Any]:
    settings = get_settings()
    if not settings.curated_books_path.exists():
        raise HTTPException(
            status_code=500,
            detail={
                "message": "curated_books.yml not found",
                "path": str(settings.curated_books_path),
            },
        )

    with settings.curated_books_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or []

    if not isinstance(data, list) or not data:
        raise HTTPException(
            status_code=500,
            detail={"message": "curated_books.yml must contain a non-empty list of books"},
        )

    candidate = random.choice(data)
    if not isinstance(candidate, dict) or "work_id" not in candidate:
        raise HTTPException(status_code=500, detail={"message": "Invalid curated_books.yml format"})

    work_id = str(candidate["work_id"])
    if work_id.startswith("/works/"):
        work_id = work_id.rsplit("/", maxsplit=1)[-1]

    return {
        "work_id": work_id,
        "title": candidate.get("title"),
        "authors": candidate.get("authors"),
    }
