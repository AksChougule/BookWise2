from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.explore_link import ExploreLink


class ExploreLinksRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_work_id(self, work_id: str) -> ExploreLink | None:
        stmt = select(ExploreLink).where(ExploreLink.work_id == work_id)
        return self.db.scalar(stmt)

    def create_or_update(
        self,
        *,
        work_id: str,
        amazon_url: str,
        goodreads_url: str,
        author_website: str | None,
    ) -> ExploreLink:
        row = self.get_by_work_id(work_id)
        if row is None:
            row = ExploreLink(
                work_id=work_id,
                amazon_url=amazon_url,
                goodreads_url=goodreads_url,
                author_website=author_website,
            )
            self.db.add(row)
        else:
            row.amazon_url = amazon_url
            row.goodreads_url = goodreads_url
            row.author_website = author_website

        self.db.commit()
        self.db.refresh(row)
        return row
