# BookWise2 — Post-MVP Foundational Sprint Spec (Engineering + Testing + Observability)

**Purpose:** Build a strong foundation so we can expand features and polish UX/UI confidently without fear of regressions.

---

## Success Criteria

By the end of this sprint:

1. Generation runs through a **formal job state machine** with safe claiming and status transitions.
2. Duplicate generation requests are **idempotent** and do not create duplicate LLM calls.
3. Prompts are **versioned and hashed**, stored on each generation, and compiled safely.
4. We have a **fast test suite** covering generation logic, API contracts, SQLite persistence, and concurrency.
5. We can diagnose failures quickly with **end-to-end correlation IDs**, metrics events, and normalized error codes.

---

## Engineering Foundations

### E1) Formalize generation into a job system (SQLite-friendly)

**Motivation:** As we add more insight types, we want a single reliable job mechanism rather than repeated ad-hoc logic.

#### Proposed Design

Option A (recommended): **Extend the existing `generations` table** with job/lease fields.

Add columns:

* `job_id` (TEXT, UUID)
* `status` enum extended to include: `queued | running | succeeded | failed` (can map to existing naming if preferred)
* `attempt` (INTEGER, default 0)
* `locked_by` (TEXT, nullable)
* `locked_at` (DATETIME/TEXT, nullable)
* `lease_expires_at` (DATETIME/TEXT, nullable)
* `started_at` (DATETIME/TEXT, nullable)
* `finished_at` (DATETIME/TEXT, nullable)

Keep:

* `work_id`, `section` with unique constraint `(work_id, section, prompt_hash, model)` **OR** keep `(work_id, section)` and store `prompt_hash/model` for informational purposes (see E2/E3).

#### State Machine

* `queued` → `running` → `succeeded`
* `queued` → `running` → `failed`
* Retry path: `failed` → `queued` (increment `attempt`)

#### Leasing / Claiming

* Claim a job by setting `locked_by`, `locked_at`, `lease_expires_at` only if:

  * job is `queued`, OR
  * job is `running` but lease has expired
* Lease duration: **60–120 seconds** (config)

**Acceptance tests (engineering):**

* Only one request can claim a job at a time.
* If a worker crashes (lease expires), another request can reclaim and continue.

---

### E2) Idempotency + exactly-once semantics for LLM calls

**Motivation:** Even with concurrency control, retries and multi-tab usage can accidentally trigger multiple LLM calls.

#### Add an idempotency concept

Compute and persist:

* `idempotency_key = sha256(work_id + section + prompt_hash + model)`
* `input_fingerprint = sha256(normalized_title + normalized_author + normalized_description)`

Persist on each generation row:

* `idempotency_key` (TEXT, indexed)
* `input_fingerprint` (TEXT)

#### Behavioral requirements

* If a request arrives and an existing row with same `idempotency_key` exists:

  * return its status/content; **do not** create a new job.
* If prompt_hash/model changed:

  * this should produce a new `idempotency_key` (and optionally allow regeneration policies later).

**Acceptance tests (engineering):**

* Repeated requests for same `work_id/section/prompt_hash/model` never cause >1 LLM call.

---

### E3) Prompt versioning + safe compilation

**Motivation:** Prevent template bugs and enable controlled prompt evolution.

#### Template Engine

* Replace Python `.format()` usage with **Jinja2** rendering.
* Use **StrictUndefined** so missing variables fail fast.

#### Prompt metadata

Persist for every generation:

* `prompt_name` (e.g., `key_ideas`, `critique`)
* `prompt_version` (e.g., `2026-03-04` or semver)
* `prompt_hash` (sha256 of final compiled prompt text)

#### Storage

* Keep prompt templates in `app/prompts/`.
* Add a small `PromptStore` service that:

  * loads templates
  * renders via Jinja2
  * returns `(compiled_prompt, prompt_version, prompt_hash)`

**Acceptance tests (engineering):**

* Prompt compilation fails with a clear error if a required variable is missing.
* `prompt_hash` changes whenever template changes.

---

## Testing Foundations

### T1) Fast unit tests for generation flow (no network)

**Goal:** Make generation logic testable without OpenAI calls.

#### Approach

* Add a `FakeLLMProvider` implementing the same interface as the OpenAI provider.
* It returns deterministic outputs for `key_ideas` and `critique`.

#### Unit tests

* First request creates/claims job and transitions statuses correctly.
* Failed generation stores `error_type` + `error_message`.
* Retry increments attempt and can succeed.

**Target runtime:** < 1–2 seconds for unit suite.

---

### T2) Contract tests for API responses

**Goal:** Prevent frontend breakage by locking API shapes.

#### Endpoints to cover

* `GET /api/search?q=`
* `GET /api/books/{work_id}`
* `GET /api/books/{work_id}/key-ideas`
* `GET /api/books/{work_id}/critique`
* `GET /api/surprise`

#### Requirements

* Validate JSON structure (keys present, types sane).
* Validate error responses include `error_type` + human-readable message.

---

### T3) Integration tests with real SQLite DB (temp file)

**Goal:** Ensure migrations + persistence behave as expected.

#### Approach

* Create temp DB per test session.
* Run Alembic migrations.
* Run API calls against FastAPI using `httpx.AsyncClient`.

#### Assertions

* Unique constraints work as intended.
* Status transitions persist.
* Prompt metadata fields are persisted.

---

### T4) Concurrency tests (most important)

**Goal:** Prove only one LLM call happens under parallel load.

#### Test

* Fire **10 parallel requests** for the same `work_id` and `section`.
* Fake provider should record how many times it was invoked.

#### Pass criteria

* Exactly **1** provider call.
* Other requests return `queued/running` then converge to `succeeded`.

---

## Observability Foundations

### O1) End-to-end correlation IDs

**Goal:** Trace a single user action through API → job claim → LLM call → DB write.

#### IDs

* `request_id`: per HTTP request (existing)
* `trace_id`: propagate across background execution/polling (new)
* `job_id`: per generation job (new)

#### Requirements

* All logs for a generation include: `trace_id`, `job_id`, `work_id`, `section`.
* API responses for generation endpoints include `job_id` and `trace_id`.

---

### O2) Metrics via structured logs (initially)

**Goal:** Track performance and reliability over time without needing full metrics infra yet.

Emit structured metric events:

* `generation_started_total{section,model}`
* `generation_succeeded_total{section,model}`
* `generation_failed_total{section,model,error_type}`
* `generation_latency_ms{section,model}`
* `cache_hit_total{section}` / `cache_miss_total{section}`
* `tokens_prompt`, `tokens_completion` per run

**Requirement:** Metrics are emitted as JSON logs (easy to export later).

---

### O3) Failure reason codes + error context

**Goal:** Make failures actionable, consistent, and user-presentable.

#### Normalize errors

Add `error_type` values:

* `provider_timeout`
* `provider_rate_limited`
* `schema_validation_failed`
* `prompt_compile_error`
* `db_error`
* `unknown`

Persist:

* `error_type` (TEXT)
* `error_message` (TEXT)
* `error_context` (JSON/TEXT)

**Requirement:** UI can show a friendly message derived from `error_type`.

---

## Data Model Changes

### Generations table (recommended additions)

We will **extend the existing `generations` table** (fastest path).

Add columns:

* `job_id` (TEXT)
* `attempt` (INTEGER, default 0)
* `locked_by` (TEXT, nullable)
* `locked_at` (DATETIME/TEXT, nullable)
* `lease_expires_at` (DATETIME/TEXT, nullable)
* `started_at` (DATETIME/TEXT, nullable)
* `finished_at` (DATETIME/TEXT, nullable)
* `idempotency_key` (TEXT, indexed)
* `input_fingerprint` (TEXT)
* `prompt_name` (TEXT)
* `prompt_version` (TEXT)
* `prompt_hash` (TEXT)
* `error_type` (TEXT)
* `error_context` (JSON/TEXT)

**Status naming decision:** keep existing statuses:

* `pending` (maps to queued)
* `generating` (maps to running)
* `completed` (maps to succeeded)
* `failed`

### Unique key strategy (decision)

Keep existing unique constraint:

* `(work_id, section)`

Add **prompt hash** for future regeneration and auditability:

* Store `prompt_hash` and `prompt_version` on every row.

(We are not changing uniqueness to include prompt hash in this sprint to minimize churn.)

---

## API Changes

No new endpoints required.

**Response enhancements (generation endpoints):**

* Include `job_id`, `trace_id`.
* Include `prompt_version`, `prompt_hash` (optional but recommended).
* Include `error_type` consistently on failure.

---

## Implementation Tasks (Deliverables)

### Deliverable A — Migration

* Alembic migration adding new columns to `generations`.
* Update SQLAlchemy model.

### Deliverable B — PromptStore (Jinja2)

* Add Jinja2 dependency.
* Implement prompt rendering + hash/version.
* Replace `.format()` usage.

### Deliverable C — Job claiming + leasing

* Implement claim logic in repository/service.
* Enforce lease expiry behavior.
* **Lease duration decision:** **100 seconds** (configurable).
* Add retry helper (increment `attempt`).

### Deliverable D — FakeLLMProvider + test harness

* Add provider stub.
* Configure DI for tests.

### Deliverable E — Test suites

* Unit tests for generation state machine.
* API contract tests.
* Integration tests with temp SQLite + migrations.
* Concurrency test (10 parallel requests).

### Deliverable F — Observability

* Add `trace_id` creation/propagation.
* Add structured metric events.
* Add normalized error codes and persistence.

---

## Acceptance Checklist

### Engineering

* [ ] **Status naming unchanged**: system continues to use `pending | generating | completed | failed`.
* [ ] **Job identity**: every generation row has a `job_id`.
* [ ] **Leasing works**: claiming sets `locked_by/locked_at/lease_expires_at`; a second claimant cannot take a non-expired lease.
* [ ] **Lease expiry works**: if `lease_expires_at` is in the past, another request can reclaim and proceed.
* [ ] **Idempotency enforced**: repeated requests for the same `work_id/section/prompt_hash/model` do not trigger >1 LLM call.
* [ ] **Prompt compilation safety**: prompts render via Jinja2; missing variables fail with `prompt_compile_error`.
* [ ] **Prompt metadata persisted**: `prompt_name`, `prompt_version`, and `prompt_hash` are stored on each generation.

### Testing

* [ ] **Unit tests (no network)**: generation flow/state transitions pass using `FakeLLMProvider`.
* [ ] **API contract tests**: endpoints return stable shapes; failures include `error_type`.
* [ ] **SQLite integration tests**: migrations run; persistence and constraints behave correctly.
* [ ] **Concurrency test**: 10 parallel requests for same `work_id/section` result in exactly **1** provider invocation and a single completed row.

### Observability

* [ ] **Correlation IDs**: logs include `request_id`, `trace_id`, and `job_id` for generation-related events.
* [ ] **Metrics emitted**: structured log events exist for started/succeeded/failed + latency + cache hit/miss.
* [ ] **Normalized failure reasons**: `error_type` stored for failures; `error_context` present for debugging.

---

## Notes / Open Decisions (Resolved)

1. **Status naming:** keep existing (`pending/generating/completed/failed`).
2. **Unique key strategy:** keep `(work_id, section)` uniqueness; **store `prompt_hash`** on every row.
3. **Lease duration:** **100 seconds**.
