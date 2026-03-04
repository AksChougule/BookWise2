import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.clients.openlibrary_client import OpenLibraryClient
from app.schemas.books import BookOut
from app.services.book_service import BookService
from app.utils.db import get_db

router = APIRouter()


@router.get("/books/{work_id}", response_model=BookOut)
async def get_book(work_id: str, db: Session = Depends(get_db)) -> BookOut:
    service = BookService(db=db, client=OpenLibraryClient())
    try:
        return await service.get_book(work_id)
    except httpx.HTTPStatusError as exc:
        status_code = 404 if exc.response.status_code == 404 else 502
        raise HTTPException(
            status_code=status_code,
            detail={
                "message": "Failed to fetch book metadata",
                "error": str(exc),
                "work_id": work_id,
            },
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Failed to fetch book metadata",
                "error": str(exc),
                "work_id": work_id,
            },
        ) from exc
