# BookWise 2 (MVP)

BookWise 2 is a local full-stack web app that lets you search Open Library, open a book page, and automatically generate:

1. `Key Ideas` (first)
2. `Critique` (queued asynchronously after Key Ideas completes)

Generated content and metadata are persisted in SQLite and reused on subsequent loads.

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
