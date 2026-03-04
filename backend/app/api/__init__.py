from fastapi import APIRouter

from app.api.books import router as books_router
from app.api.generation import router as generation_router
from app.api.search import router as search_router
from app.api.surprise import router as surprise_router

api_router = APIRouter()
api_router.include_router(search_router)
api_router.include_router(books_router)
api_router.include_router(generation_router)
api_router.include_router(surprise_router)
