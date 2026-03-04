# BookWise Timeout Debugging

## Reproduce

1. Start backend (for timeout debugging, avoid reload):

```bash
cd backend
poetry install
poetry run alembic upgrade head
poetry run uvicorn app.main:app --port 8000
```

2. Start frontend:

```bash
cd frontend
npm install
npm run dev
```

3. Open `http://localhost:5173`, run Search or Surprise Me, then open DevTools console.

## Logs To Watch

Backend logs are JSON and include `request_id`, `route`, `work_id`, `section`, `status`, `duration_ms`.

Key events:
- `request_started` / `request_completed`
- `generation_state_snapshot`
- `generation_started` / `generation_completed` / `generation_failed`
- `openai_request_started` / `openai_request_completed` / `openai_request_failed`
- `openai_retrying`

Frontend console events:
- `[poll]` with `attempt`, `endpoint`, `status`, `request_id`

Use request IDs to correlate frontend polls to backend logs.

## Inspect SQLite Generation Rows

```bash
cd backend
poetry run python -c "import sqlite3; c=sqlite3.connect('bookwise.db');
rows=c.execute('select work_id,section,status,model,error_message,tokens_prompt,tokens_completion,generation_time_ms,updated_at from generations order by updated_at desc limit 20').fetchall();
print(*rows, sep='\n')"
```

## Quick Health Checks

Check config loaded by backend process:

```bash
cd backend
poetry run python -c "from app.config import get_settings; s=get_settings(); print('openai_key_present=', bool(s.openai_api_key)); print('model=', s.openai_model)"
```

If failures happen, API should return generation status `failed` with detailed `error_message` instead of staying `generating`.
