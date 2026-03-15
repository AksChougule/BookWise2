# BookWise 
## Never Miss the Big Ideas

Books are an amazing way to consume knowledge, but retaining that knowledge is challenging. If we can't retain the insights, it becomes harder to test these ideas and apply them meaningfully in our lives.

Research on the forgetting curve shows that within 24 hours, learners forget an average of 70% of new information, and within a week, they forget up to 90%. [source](https://www.indegene.com/what-we-think/reports/understanding-science-behind-learning-retention)

I have repeatedly experienced this myself - while reading, I find certain books highly insightful, but weeks later I struggle to recall most of what mattered. Discussing a book with friends and family can help you retain information longer, but you can only revisit what you've already remembered at the time of conversation. The insights you've forgotten remain lost.

That's why I built BookWise: to help you refresh your memory so the big ideas don't fade away. This isn't Goodreads where you browse reviews—it's a focused tool designed to help you spend quality time with your favorite books and truly internalize their insights.

BookWise is a local full-stack web app that lets you search Open Library, open a book page, and automatically generate:

1. `Book Summary`
2. `Key Ideas` 
3. `Critique`
4. `Realted Videos and Podcasts`
5. `External links` to explore more like purchase on Amazon, reviews on Goodreads, author's website


Generated content and metadata are persisted in SQLite and reused on subsequent loads.

## Screenshots

Landing Page with instant search
<img width="1253" height="979" alt="Screenshot from 2026-03-11 21-34-13" src="https://github.com/user-attachments/assets/ab8baf92-6c67-4738-a3b4-174f14528922" />


Book Summary
<img width="1108" height="719" alt="Screenshot from 2026-03-11 22-14-26" src="https://github.com/user-attachments/assets/47cc9105-b32d-47b7-9987-c35d9494e9e9" />


Key Ideas from the Book
<img width="1153" height="920" alt="Screenshot from 2026-03-11 21-50-08" src="https://github.com/user-attachments/assets/11194dea-6c44-4762-b5f6-42c3764c4c68" />


Book Critique
<img width="1118" height="941" alt="Screenshot from 2026-03-11 22-16-39" src="https://github.com/user-attachments/assets/63e3218f-872a-42e1-be17-2ec40b9dff36" />


Book Related Videos
<img width="1148" height="937" alt="Screenshot from 2026-03-11 21-56-35" src="https://github.com/user-attachments/assets/a0265708-f0c4-4678-976b-16590af2eab6" />


Other books by same author (with one click insights)
<img width="1151" height="916" alt="Screenshot from 2026-03-11 21-53-02" src="https://github.com/user-attachments/assets/9cacc51e-a7c7-47b3-b445-6c1b67da3e03" />


## Stack

- Backend: FastAPI, SQLAlchemy 2.0, Alembic, Poetry
- Frontend: React + Vite + TypeScript
- DB: SQLite
- LLM provider: OpenAI (pluggable provider architecture)

## Project Layout

- `backend/` FastAPI app 
- `frontend/` Vite React app
- `curated_books.yml` curated list of Books for the "Surprise Me" option

## Prerequisites

- Python `3.12+`
- Poetry `2.x`
- Node `20+`
- npm `10+`
- OpenAI API key
- YouTube Search API key (optional)

## Docker Quick Start

For local Docker setup (frontend + backend + SQLite persistence + secrets), see [DOCKER.md](DOCKER.md).

## API Endpoints

- `GET /api/search?q=...`
- `GET /api/books/{work_id}`
- `GET /api/books/{work_id}/key-ideas`
- `GET /api/books/{work_id}/critique`
- `GET /api/surprise`