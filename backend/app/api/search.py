import httpx
from fastapi import APIRouter, HTTPException, Query

from app.clients.openlibrary_client import OpenLibraryClient
from app.schemas.books import SearchResponse
from app.services.search_service import SearchService

router = APIRouter()


@router.get("/search", response_model=SearchResponse)
async def search_books(q: str = Query(..., min_length=1)) -> SearchResponse:
    service = SearchService(client=OpenLibraryClient())
    try:
        return await service.search(q)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Open Library search failed",
                "error": str(exc),
                "query": q,
            },
        ) from exc
