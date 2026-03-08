import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.clients.openlibrary_client import OpenLibraryClient
from app.clients.youtube_client import YouTubeClient
from app.repositories.explore_links_repo import ExploreLinksRepository
from app.repositories.youtube_repo import YouTubeRepository
from app.schemas.external_sections import AuthorBooksOut, ExploreLinksOut, YouTubeVideosOut
from app.services.author_books_service import AuthorBooksService
from app.services.book_service import BookService
from app.services.explore_links_service import ExploreLinksService
from app.services.youtube_service import YouTubeService
from app.utils.db import get_db

router = APIRouter()


@router.get("/books/{work_id}/other-books", response_model=AuthorBooksOut)
async def get_other_books_by_author(work_id: str, db: Session = Depends(get_db)) -> AuthorBooksOut:
    try:
        book = await BookService(db=db, client=OpenLibraryClient()).get_book(work_id)
    except httpx.HTTPStatusError as exc:
        status_code = 404 if exc.response.status_code == 404 else 502
        raise HTTPException(
            status_code=status_code,
            detail={
                "message": "Failed to fetch book metadata before author books",
                "error": str(exc),
                "work_id": work_id,
                "section": "other_books",
            },
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Failed to fetch book metadata before author books",
                "error": str(exc),
                "work_id": work_id,
                "section": "other_books",
            },
        ) from exc

    service = AuthorBooksService(client=OpenLibraryClient())
    try:
        return await service.fetch_for_book(work_id=work_id, authors_text=book.authors)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Failed to fetch other books by author",
                "error": str(exc),
                "work_id": work_id,
                "section": "other_books",
            },
        ) from exc


@router.get("/books/{work_id}/youtube-videos", response_model=YouTubeVideosOut)
async def get_youtube_videos(work_id: str, db: Session = Depends(get_db)) -> YouTubeVideosOut:
    try:
        book = await BookService(db=db, client=OpenLibraryClient()).get_book(work_id)
    except httpx.HTTPStatusError as exc:
        status_code = 404 if exc.response.status_code == 404 else 502
        raise HTTPException(
            status_code=status_code,
            detail={
                "message": "Failed to fetch book metadata before youtube videos",
                "error": str(exc),
                "work_id": work_id,
                "section": "youtube_videos",
            },
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Failed to fetch book metadata before youtube videos",
                "error": str(exc),
                "work_id": work_id,
                "section": "youtube_videos",
            },
        ) from exc

    service = YouTubeService(repo=YouTubeRepository(db), client=YouTubeClient())
    try:
        return await service.get_for_book(work_id=work_id, title=book.title, authors_text=book.authors)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "YouTube integration is not configured",
                "error": str(exc),
                "work_id": work_id,
                "section": "youtube_videos",
            },
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Failed to fetch youtube videos",
                "error": str(exc),
                "work_id": work_id,
                "section": "youtube_videos",
            },
        ) from exc


@router.get("/books/{work_id}/explore-more", response_model=ExploreLinksOut)
async def get_explore_more(work_id: str, db: Session = Depends(get_db)) -> ExploreLinksOut:
    try:
        book = await BookService(db=db, client=OpenLibraryClient()).get_book(work_id)
    except httpx.HTTPStatusError as exc:
        status_code = 404 if exc.response.status_code == 404 else 502
        raise HTTPException(
            status_code=status_code,
            detail={
                "message": "Failed to fetch book metadata before explore links",
                "error": str(exc),
                "work_id": work_id,
                "section": "explore_more",
            },
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Failed to fetch book metadata before explore links",
                "error": str(exc),
                "work_id": work_id,
                "section": "explore_more",
            },
        ) from exc

    service = ExploreLinksService(repo=ExploreLinksRepository(db), client=OpenLibraryClient())
    try:
        return await service.get_for_book(work_id=work_id, title=book.title, authors_text=book.authors)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Failed to resolve explore links",
                "error": str(exc),
                "work_id": work_id,
                "section": "explore_more",
            },
        ) from exc
