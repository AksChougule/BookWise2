# Job Leasing Behavior (Generation Pipeline)

This document describes how BookWise2 currently enforces single-worker execution for LLM generation jobs (`key_ideas`, `critique`).

## Scope

Leasing applies to generation rows in the `generations` table, uniquely identified by `(work_id, section)`.

Status values remain:
- `pending`
- `generating`
- `completed`
- `failed`

Lease duration is fixed by config:
- `generation_lease_seconds = 100`

## Data Model Fields

Generation rows include lease metadata:
- `locked_by`: worker identifier that currently holds the lease (current format: `pid-<process_id>`)
- `locked_at`: UTC timestamp when lease was claimed
- `lease_expires_at`: UTC timestamp when current lease becomes reclaimable
- `finished_at`: UTC timestamp set when generation finishes (success or failure)

## Claim Rules

A request attempts to claim a generation job through `GenerationRepository.claim_job(...)`.

A claim succeeds only when **one** of the following is true for the target row:
1. `status` is `pending`
2. `status` is `failed`
3. `status` is `generating` **and** lease is expired:
   - `lease_expires_at <= now`, or
   - `lease_expires_at` is `NULL`

If a claim succeeds, repository updates:
- `status = generating`
- `error_message = NULL`
- `locked_by = <worker_id>`
- `locked_at = now`
- `lease_expires_at = now + 100 seconds`
- `finished_at = NULL`
- `updated_at = now`

If a claim fails (active lease held by another worker), no LLM call is started and current job status is returned.

## Execution Flow

### Key Ideas (`/api/books/{work_id}/key-ideas`)
1. Ensure generation row exists (`get_or_create`).
2. If already `completed`, return cached content.
3. Attempt lease claim.
4. If claim succeeds, run generation.
5. If claim fails, return current state (`generating` or other current status).

### Critique (`/api/books/{work_id}/critique`)
1. Ensure critique row exists.
2. Require key ideas row to be `completed`; otherwise return current critique status.
3. If already `completed`, return cached content.
4. Attempt lease claim.
5. If claim succeeds, run generation.
6. If claim fails, return current state.

## Lease Release on Finish

On successful generation (`mark_completed`):
- `status = completed`
- content/tokens/model metadata saved
- lease cleared:
  - `locked_by = NULL`
  - `locked_at = NULL`
  - `lease_expires_at = NULL`
- `finished_at = now`

On failed generation (`mark_failed`):
- `status = failed`
- `error_message` persisted
- lease cleared:
  - `locked_by = NULL`
  - `locked_at = NULL`
  - `lease_expires_at = NULL`
- `finished_at = now`

## Crash Recovery / Reclaim

If a worker crashes while status is `generating`, lease fields remain populated.
A later request can reclaim and continue work only after lease expiration (`~100s`).

This prevents duplicate concurrent LLM calls while still allowing recovery from interrupted workers.

## Interaction with Idempotency

Leasing controls concurrent execution for a specific `(work_id, section)` row.
Idempotency logic (based on `idempotency_key`) prevents duplicate generation work across repeated equivalent requests.

Both protections are active:
- idempotency checks avoid unnecessary generation when equivalent output already exists
- leasing ensures only one active generator can run at a time for the row

## Operational Notes

- Migration introducing lease fields: `backend/alembic/versions/0004_generation_leases.py`
- Default lease duration source: `backend/app/config.py`
- Core claim logic: `backend/app/repositories/generation_repo.py` (`claim_job`)
- Service integration: `backend/app/services/generation_service.py`
- Tests: `backend/tests/test_generation_leasing.py`
