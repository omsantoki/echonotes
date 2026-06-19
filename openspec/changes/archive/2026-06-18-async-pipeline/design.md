## Context

The pipeline ran via FastAPI `BackgroundTasks`, i.e. inside the web (uvicorn) process. That gave the 202-then-poll UX but no durability: a deploy/crash killed in-flight pipelines (mitigated only by marking interrupted lectures `failed` on startup), and heavy work competed with request handling. The product already targets a stateless backend on Render with managed Postgres/Qdrant/S3, so introducing a managed Redis and a separate worker service fits the existing topology.

## Goals / Non-Goals

**Goals:**
- Durable, retryable processing of the lecture pipeline off the web process.
- Independent scaling of workers from the API.
- Preserve the existing client contract (POST → 202 → poll status) and the pipeline body (`run_pipeline`) unchanged.
- Zero extra infrastructure for local dev and the hermetic test suite.

**Non-Goals:**
- Sharing uploaded files across separate web/worker hosts (uploads still land in a local temp workdir — documented constraint; a later change moves them to object storage).
- Replacing the polling status model with websockets/SSE.
- A user-visible job/queue dashboard.

## Decisions

- **Celery + Redis** (broker + result backend) over RQ/Dramatiq/cloud queues: Celery is the mature default, Redis is a single dependency that also backs the semantic cache (see the `qa-semantic-cache` change), and it deploys cleanly as one Render instance.
- **Wrap, don't rewrite.** `process_lecture` is a thin `@celery_app.task` that calls the existing `run_pipeline(...)`. The pipeline keeps writing its own progress/status and cleaning its temp workdir, so the polling UI and Art. IV guarantees are untouched.
- **Eager mode for dev/test.** `task_always_eager` (default `true`) makes `.delay()` run inline in the caller. With a blank `REDIS_URL`, broker/result URLs fall back to in-memory values that eager mode never touches. Production sets `REDIS_URL` + `TASK_ALWAYS_EAGER=false`. This keeps the suite hermetic with no broker and no new mandatory dependency at runtime.
- **Durability knobs:** `task_acks_late=true` + `worker_prefetch_multiplier=1` (re-deliver if a worker dies mid-task; one heavy task at a time), `autoretry_for=(ConnectionError, TimeoutError)` with `retry_backoff` and `max_retries=2`. The pipeline's own try/except still records a terminal `failed` for non-transient errors.
- **Startup recovery retained.** The lifespan handler that flips orphaned `processing` lectures to `failed` stays as a backstop; it becomes rare once retries handle transient worker death.

## Risks / Trade-offs

- [Separate worker host can't read the web host's local temp workdir] → For v1 run web+worker on a shared disk or keep `TASK_ALWAYS_EAGER=true`; documented in `render.yaml`. Follow-up: write uploads to the existing S3 backend.
- [Redis unavailable in production] → Tasks won't enqueue/process; surfaced via `/api/health` `async` block. Operationally, Redis is a managed instance with `maxmemoryPolicy=noeviction` so queued tasks aren't dropped under pressure.
- [Eager mode hides real async timing in tests] → Acceptable: tests assert the *enqueue contract* (task is dispatched) and the pipeline is tested directly; true broker behavior is verified manually (see tasks).
- [Worker env drift] → The worker runs the same app and needs the same provider/model/storage env as the web service; `render.yaml` documents this (Render does not auto-share env across services).

## Migration Plan

1. Deploy with `TASK_ALWAYS_EAGER=true` (web runs inline) — behavior identical to today, new deps inert.
2. Provision the Redis instance + worker service; set `REDIS_URL` on both and flip `TASK_ALWAYS_EAGER=false` (after shared upload storage is in place, or while co-located).
3. Rollback: set `TASK_ALWAYS_EAGER=true` on the web service — uploads process inline again; no data migration involved.

## Open Questions

- Move the upload workdir to S3 now or in a dedicated follow-up change? (Currently deferred.)
