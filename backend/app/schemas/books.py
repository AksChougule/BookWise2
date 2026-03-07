from datetime import datetime

from pydantic import BaseModel, Field


class SearchBookOut(BaseModel):
    work_id: str
    title: str
    authors: str | None = None
    first_publish_year: int | None = None
    cover_url: str | None = None


class SearchResponse(BaseModel):
    query: str
    count: int
    results: list[SearchBookOut]


class BookOut(BaseModel):
    work_id: str
    title: str
    authors: str | None = None
    description: str | None = None
    cover_url: str | None = None
    subjects: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
