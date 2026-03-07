import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.clients.openlibrary_client import OpenLibraryClient
from app.schemas.generations import CritiqueOut, KeyIdeasOut, SummaryOut
from app.services.book_service import BookService
from app.services.generation_service import GenerationService
from app.utils.db import get_db

router = APIRouter()


@router.get("/books/{work_id}/key-ideas", response_model=KeyIdeasOut)
async def get_key_ideas(
    work_id: str,
    retry: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> KeyIdeasOut:
    try:
        # Ensure the book exists before generation starts.
        await BookService(db=db, client=OpenLibraryClient()).get_book(work_id)
    except httpx.HTTPStatusError as exc:
        status_code = 404 if exc.response.status_code == 404 else 502
        raise HTTPException(
            status_code=status_code,
            detail={
                "message": "Failed to fetch book metadata before key ideas generation",
                "error": str(exc),
                "work_id": work_id,
                "section": "key_ideas",
            },
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Failed to fetch book metadata before key ideas generation",
                "error": str(exc),
                "work_id": work_id,
                "section": "key_ideas",
            },
        ) from exc

    service = GenerationService(db)
    return await service.trigger_key_ideas(work_id, retry=retry)


@router.get("/books/{work_id}/critique", response_model=CritiqueOut)
async def get_critique(
    work_id: str,
    retry: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> CritiqueOut:
    try:
        # Ensure the book exists for direct endpoint access.
        await BookService(db=db, client=OpenLibraryClient()).get_book(work_id)
    except httpx.HTTPStatusError as exc:
        status_code = 404 if exc.response.status_code == 404 else 502
        raise HTTPException(
            status_code=status_code,
            detail={
                "message": "Failed to fetch book metadata before critique status check",
                "error": str(exc),
                "work_id": work_id,
                "section": "critique",
            },
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Failed to fetch book metadata before critique status check",
                "error": str(exc),
                "work_id": work_id,
                "section": "critique",
            },
        ) from exc

    service = GenerationService(db)
    return await service.get_or_create_critique_status(work_id, retry=retry)


@router.get("/books/{work_id}/summary", response_model=SummaryOut)
async def get_summary(
    work_id: str,
    retry: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> SummaryOut:
    try:
        await BookService(db=db, client=OpenLibraryClient()).get_book(work_id)
    except httpx.HTTPStatusError as exc:
        status_code = 404 if exc.response.status_code == 404 else 502
        raise HTTPException(
            status_code=status_code,
            detail={
                "message": "Failed to fetch book metadata before summary",
                "error": str(exc),
                "work_id": work_id,
                "section": "summary_llm",
            },
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Failed to fetch book metadata before summary",
                "error": str(exc),
                "work_id": work_id,
                "section": "summary_llm",
            },
        ) from exc

    service = GenerationService(db)
    return await service.get_or_generate_summary(work_id, retry=retry)
