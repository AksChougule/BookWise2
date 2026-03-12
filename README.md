# BookWise 2 (MVP)

BookWise 2 is a local full-stack web app that lets you search Open Library, open a book page, and automatically generate:

1. `Book Summary`
2. `Key Ideas` 
3. `Critique` (queued asynchronously after Key Ideas completes)
4. `Realted Videos` and Podcast episodes
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

- `backend/` FastAPI app (`api/services/repositories/clients/models/schemas/prompts/utils`)
- `frontend/` Vite React app
- `curated_books.yml` curated data for Surprise Me

## Prerequisites

- Python `3.12+`
- Poetry `2.x`
- Node `20+`
- npm `10+`
- OpenAI API key

## Backend Setup

```bash
cd backend
cp .env.example .env
# edit .env and set OPENAI_API_KEY

poetry install
poetry run alembic upgrade head
poetry run uvicorn app.main:app --port 8000
```

Backend docs: `http://localhost:8000/docs`

### Backend Environment Variables

- `OPENAI_API_KEY` (required for generation)
- `OPENAI_MODEL` (optional, default: `gpt-5.2`)
- `BOOKWISE_DB_URL` (optional, default: `sqlite:///./bookwise.db`)

## Frontend Setup

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Frontend: `http://localhost:5173`

## MVP User Flows

- Search flow:
  - `/` search for books
  - open `/book/:workId`
  - frontend polls `/api/books/{work_id}/key-ideas` first, then `/api/books/{work_id}/critique` after key ideas completes
- Surprise flow:
  - click `Surprise Me` (calls `/api/surprise`)
  - app navigates to `/book/:workId`
  - generation starts automatically if missing

## API Endpoints

- `GET /api/search?q=...`
- `GET /api/books/{work_id}`
- `GET /api/books/{work_id}/key-ideas`
- `GET /api/books/{work_id}/critique`
- `GET /api/surprise`

## Generation Behavior

- Prompt context sent to LLM: title + author only
- Token caps:
  - Key Ideas: `5000`
  - Critique: `2000`
- Concurrency control:
  - DB row claim (`pending/failed -> generating`) prevents duplicate LLM calls for same `work_id + section`
- Critique generation starts only after Key Ideas is completed
- Generation results are cached and reused (no regenerate button in MVP)

## Polling and UI Error Handling

- Polls each section every 5 seconds, max 18 retries (~90s window)
- Shows skeleton with `Please wait...` while pending/generating
- If failed: displays detailed `error_message`, `section`, `model`
- If still pending after max retries: displays timeout error

## Observability

- Structured JSON logs
- `request_id` middleware with `X-Request-ID` response header
- Generation event logs include section/model/duration/token usage/errors
