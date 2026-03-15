# BookWise Docker Setup

This repository includes a local, developer-friendly Docker setup for BookWise:
- `frontend` runs the Vite dev server on port `5173`
- `backend` runs FastAPI/Uvicorn on port `8000`
- SQLite data persists in a Docker named volume (`bookwise_sqlite_data`)
- API keys are mounted as Docker Compose secrets (never baked into images)

## Prerequisites

- Docker Desktop (Mac/Windows) or Docker Engine + Docker Compose v2 (Linux)
- Git

## 1. Create Secret Files

From the repo root:

```bash
mkdir -p secrets
printf 'YOUR_OPENAI_API_KEY' > secrets/openai_api_key
printf 'YOUR_YOUTUBE_API_KEY' > secrets/youtube_api_key
```

Notes:
- `openai_api_key` is required only when generation endpoints are used.
- `youtube_api_key` is optional for core app flow; if missing/empty, YouTube section degrades gracefully.
- Do not commit `secrets/`.

## 2. Start BookWise

From repo root:

```bash
docker compose up --build
```

## 3. URLs

- Frontend: `http://localhost:5173`
- Backend API docs: `http://localhost:8000/docs`
- Backend healthcheck endpoint: `http://localhost:8000/health`

## 4. How Persistence Works

- Backend uses `DATABASE_URL=sqlite:////app/data/bookwise.db`
- Compose mounts named volume `bookwise_sqlite_data` at `/app/data`
- Data survives container restarts/rebuilds until the volume is removed

## 5. Stop Containers

```bash
docker compose down
```

## 6. Full Reset (Containers + Volumes)

Use this when you want a clean slate, including SQLite data:

```bash
docker compose down -v
```

Then start again:

```bash
docker compose up --build
```

## Troubleshooting

### Missing secret file

Symptom: Compose fails with a secret file error.

Fix:
- Ensure files exist:
  - `secrets/openai_api_key`
  - `secrets/youtube_api_key`
- Ensure readable permissions for your user.

### Frontend loads but API calls fail

Checks:
- Confirm backend is running and healthy:
  - `docker compose ps`
  - `curl http://localhost:8000/health`
- Confirm frontend proxy target is `http://backend:8000` in `docker-compose.yml`.

### Backend unhealthy

Checks:
- `docker compose logs backend`
- Confirm `/health` responds on host:
  - `curl http://localhost:8000/health`
- Confirm SQLite path is writable in container (`/app/data`) and volume is mounted.

### Port already in use

Symptom: startup error for `5173` or `8000`.

Fix options:
- Stop local services using those ports.
- Or change Compose port mappings in `docker-compose.yml`.

### Reset persisted data

Use:

```bash
docker compose down -v
```

This removes the SQLite named volume and all persisted app data.

## Acceptance Checklist

- [ ] `docker compose up --build` starts both services
- [ ] Frontend opens at `http://localhost:5173`
- [ ] Backend health is `{"status":"ok"}` at `http://localhost:8000/health`
- [ ] Search works from frontend
- [ ] Data persists after `docker compose down` then `docker compose up`
