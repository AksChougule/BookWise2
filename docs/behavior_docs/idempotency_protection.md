# Idempotency Protection (Current Behavior)

This document describes the **current implemented idempotency behavior** for LLM generation in BookWise2.

## Scope

Idempotency applies to generation endpoints:
- `GET /api/books/{work_id}/key-ideas`
- `GET /api/books/{work_id}/critique`

It prevents duplicate LLM calls for equivalent generation inputs.

## Data persisted

The `generations` table stores:
- `idempotency_key` (TEXT, indexed)
- `input_fingerprint` (TEXT)
- `prompt_name` (TEXT)
- `prompt_version` (TEXT)
- `prompt_hash` (TEXT)

Status values remain unchanged:
- `pending`
- `generating`
- `completed`
- `failed`

Unique key strategy remains unchanged:
- unique constraint on `(work_id, section)`

## How keys are computed

Implementation lives in:
- `backend/app/utils/idempotency.py`

### 1) `input_fingerprint`

```
sha256(normalized(title) + "|" + normalized(authors) + "|" + normalized(description))
```

Normalization rules:
- trim whitespace
- collapse repeated whitespace to one space
- lowercase
- `None` becomes empty string

### 2) `idempotency_key`

```
sha256(work_id + "|" + section + "|" + prompt_hash + "|" + model)
```

Where:
- `prompt_hash` comes from compiled prompt text (PromptStore)
- `model` is current provider model from settings

## Request flow (current)

Implementation lives in:
- `backend/app/services/generation_service.py`
- `backend/app/repositories/generation_repo.py`

### Key Ideas flow

1. Load cached `Book` metadata.
2. Compile prompt via `PromptStore` (`key_ideas`), producing:
   - `compiled_prompt`
   - `prompt_version`
   - `prompt_hash`
3. Compute:
   - `input_fingerprint`
   - `idempotency_key`
4. Query `generations` by `idempotency_key`.
   - If found: return existing row immediately (no new generation).
5. Otherwise:
   - `get_or_create(work_id, section)`
   - persist prompt/idempotency fields with `set_idempotency_fields(...)`
   - attempt atomic claim (`claim_for_generation(...)`)
6. If claimed, run LLM call and update row to:
   - `completed` with content + metadata, or
   - `failed` with error + metadata.

### Critique flow

Same pattern as Key Ideas, but only after Key Ideas is `completed`.

## Repository methods used

- `get_by_idempotency_key(idempotency_key)`
- `set_idempotency_fields(...)`
- `claim_for_generation(work_id, section)`
- `mark_completed(...)`
- `mark_failed(...)`

## Why this avoids duplicate LLM calls

Two layers protect against duplicates:

1. **Idempotency lookup**
- Repeated equivalent requests resolve to same `idempotency_key` and return existing row.

2. **Atomic claim gate**
- Even under concurrency, only one request can transition row to `generating`.
- Others observe `generating/completed/failed` and do not duplicate provider calls.

## Behavior when prompt/model changes

Because `idempotency_key` includes `prompt_hash` and `model`:
- Prompt content changes => new `prompt_hash` => new key.
- Model change => new key.

Given current unique constraint `(work_id, section)`, metadata is updated on the same row rather than creating multiple rows per prompt/model variant.

## Error path

On failures, row is updated to `failed` and stores:
- `error_message`
- prompt metadata
- idempotency fields

If prompt compilation fails, error message is prefixed with:
- `prompt_compile_error: ...`

## Observability

Repository/service logs include idempotency-related events, including:
- DB reads by idempotency key
- idempotency metadata persistence
- generation status transitions

## Current limitations

1. Indexed, but not unique:
- `idempotency_key` is indexed for lookup, not unique constrained.

2. Single-row uniqueness still dominates:
- `(work_id, section)` uniqueness means no historical parallel rows per different prompt/model.

3. Idempotency relies on prompt compilation availability:
- If prompt compilation fails, idempotency key cannot be computed for that run.

## Reference files

- `backend/app/utils/idempotency.py`
- `backend/app/services/generation_service.py`
- `backend/app/repositories/generation_repo.py`
- `backend/app/models/generation.py`
- `backend/alembic/versions/0003_generation_idempotency.py`
