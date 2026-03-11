# Observability Behavior

This document describes the current observability implementation in BookWise2 backend.

## Objectives

The implementation provides:
- Request-scoped correlation (`request_id`, `trace_id`)
- Generation job correlation (`job_id`)
- Structured JSON logs for requests and generation lifecycle
- Normalized error classification with persisted error metadata
- Token/latency metrics for generation calls

## Logging Format

All backend logs are JSON-formatted via `JsonFormatter`.

Core fields on every log line:
- `timestamp`
- `level`
- `logger`
- `message`
- `request_id`
- `trace_id`

Additional contextual fields are attached per event (route, section, work_id, etc.).

Implementation:
- `backend/app/utils/logging.py`

## Request Context Propagation

HTTP middleware sets and propagates correlation IDs:

- `request_id`
  - Source: incoming `X-Request-ID` header, or generated UUID
  - Returned in response header: `X-Request-ID`

- `trace_id`
  - Source: incoming `X-Trace-ID` header, or generated UUID
  - Returned in response header: `X-Trace-ID`

Request lifecycle events emitted:
- `request_started`
- `request_completed`
- `request_failed`

Each includes request metadata (route/method/path/query) and timing (`duration_ms` on complete/fail).

Implementation:
- `backend/app/main.py`

## Generation Correlation (`job_id`)

Each generation row can carry a stable `job_id`.

Behavior:
- `job_id` is ensured before running generation (`ensure_job_id`)
- If absent, a UUID is created and persisted
- The same `job_id` is propagated through:
  - generation claim/start logs
  - completion/failure logs
  - DB commit/read logs for generation rows

This enables end-to-end tracing of one generation execution across retries/polls.

Implementation:
- `backend/app/repositories/generation_repo.py`
- `backend/app/services/generation_service.py`

## Generation Lifecycle Events

The service emits structured lifecycle metrics:
- `generation_started`
- `generation_completed`
- `generation_failed`

Included fields (as implemented):
- `work_id`
- `section`
- `job_id`
- `model`
- `latency_ms`
- `tokens_prompt`
- `tokens_completion`
- `status` (when applicable)
- `error_type` and `error_message` on failures

Notes:
- `generation_started` currently logs `latency_ms=0` because execution has just begun.
- Completed events include token usage and final latency from persisted generation data.

Implementation:
- `backend/app/services/generation_service.py`

## State Snapshot Events

On generation status reads, service emits:
- `generation_state_snapshot`

Fields include:
- `route`
- `work_id`
- `section`
- `job_id`
- `status`
- `updated_at`

Used to inspect polling behavior and state transitions.

Implementation:
- `backend/app/services/generation_service.py`

## OpenAI Provider Observability

Provider emits request-level events for OpenAI responses API:
- `openai_request_started`
- `openai_request_completed`
- `openai_request_failed`
- `openai_retrying` (tenacity retry hook)

Included fields (depending on event):
- `route` (`/v1/responses`)
- `model`
- `duration_ms`
- `status_code`
- retry metadata (`attempt_number`, `next_sleep_s`)

Implementation:
- `backend/app/providers/openai_provider.py`

## Normalized Error Types

Failures are normalized to the following values:
- `provider_timeout`
- `provider_rate_limited`
- `schema_validation_failed`
- `prompt_compile_error`
- `db_error`
- `unknown`

Classification source:
- `PromptCompileError` -> `prompt_compile_error`
- `pydantic.ValidationError` -> `schema_validation_failed`
- `ProviderError` carries `error_type` from provider
- `httpx.TimeoutException`/`ConnectError` -> `provider_timeout`
- `SQLAlchemyError` -> `db_error`
- fallback -> `unknown`

Implementation:
- `backend/app/services/generation_service.py` (`_error_payload`)

## Error Persistence

On failed generation, repository persists:
- `status = failed`
- `error_message`
- `error_type`
- `error_context` (JSON string)
- lease cleared (`locked_by`, `locked_at`, `lease_expires_at`)
- `finished_at`

On success, error fields are cleared:
- `error_type = NULL`
- `error_context = NULL`

Implementation:
- `backend/app/repositories/generation_repo.py`

## Database Schema Additions for Observability

Current `generations` table observability columns:
- `job_id` (indexed)
- `error_type`
- `error_context`

Migration:
- `backend/alembic/versions/0005_generation_observability.py`

## Related Existing Observability Signals

Also present from previous work:
- request/response logging with request IDs
- generation duration/token/model logging
- lease metadata (`locked_by`, `locked_at`, `lease_expires_at`, `finished_at`)
- startup configuration log includes `openai_key_present`, model, db url

## How To Inspect Quickly

Examples while running backend:

```bash
# stream generation lifecycle lines
poetry run uvicorn app.main:app --reload --port 8000 | rg 'generation_(started|completed|failed)|generation_state_snapshot'

# inspect persisted failure metadata
sqlite3 bookwise.db "select work_id, section, status, error_type, substr(error_message,1,120), substr(error_context,1,160), job_id, updated_at from generations order by updated_at desc limit 20;"
```

## Files Involved

- `backend/app/utils/logging.py`
- `backend/app/main.py`
- `backend/app/services/generation_service.py`
- `backend/app/repositories/generation_repo.py`
- `backend/app/providers/base_provider.py`
- `backend/app/providers/openai_provider.py`
- `backend/app/models/generation.py`
- `backend/alembic/versions/0005_generation_observability.py`
