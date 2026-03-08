from datetime import datetime

from pydantic import BaseModel


class AuthorBookItemOut(BaseModel):
    work_id: str
    title: str
    authors: str | None = None
    first_publish_year: int | None = None
    cover_url: str | None = None


class AuthorBooksGroupOut(BaseModel):
    author: str
    books: list[AuthorBookItemOut]


class AuthorBooksOut(BaseModel):
    work_id: str
    groups: list[AuthorBooksGroupOut]


class YouTubeVideoOut(BaseModel):
    video_id: str
    title: str
    channel: str
    views: int
    published_at: datetime | None = None
    thumbnail: str | None = None


class YouTubeVideosOut(BaseModel):
    work_id: str
    source: str
    videos: list[YouTubeVideoOut]


class ExploreLinksOut(BaseModel):
    work_id: str
    source: str
    amazon_url: str
    goodreads_url: str
    author_website: str | None = None
