from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.youtube_video import YouTubeVideo


class YouTubeRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_by_work_id(self, work_id: str) -> list[YouTubeVideo]:
        stmt = (
            select(YouTubeVideo)
            .where(YouTubeVideo.work_id == work_id)
            .order_by(YouTubeVideo.views.desc(), YouTubeVideo.created_at.desc())
        )
        return list(self.db.scalars(stmt))

    def replace_for_work(self, *, work_id: str, videos: list[dict]) -> list[YouTubeVideo]:
        self.db.execute(delete(YouTubeVideo).where(YouTubeVideo.work_id == work_id))
        now = datetime.now(UTC)
        rows: list[YouTubeVideo] = []
        for video in videos:
            row = YouTubeVideo(
                work_id=work_id,
                video_id=video["video_id"],
                title=video["title"],
                channel=video["channel"],
                views=video["views"],
                published_at=video.get("published_at"),
                thumbnail=video.get("thumbnail"),
                created_at=now,
            )
            self.db.add(row)
            rows.append(row)

        self.db.commit()
        for row in rows:
            self.db.refresh(row)
        return rows
