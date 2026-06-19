## Why

The lecture pipeline (transcribe → slides → align → merge → refine → diagrams → embed) is slow and CPU-heavy. It previously ran inside the web process via FastAPI `BackgroundTasks`, so a deploy or crash silently lost in-flight work, concurrent uploads contended for the web process's CPU, and workers could not scale independently. Moving the work onto a durable broker-backed task queue decouples *accepting* an upload from *processing* it, with retries and independent scaling.

## What Changes

- Lecture upload still returns **202 Accepted** immediately, but now **enqueues** the pipeline onto a Celery task queue (Redis broker + result backend) instead of running it via in-process `BackgroundTasks`.
- A **separate worker pool** (`celery -A app.worker worker`) executes the pipeline; transient failures (network/STT/LLM/vector-store) are retried with backoff (durability).
- The existing `run_pipeline` work function is unchanged — it is wrapped by a Celery task (`process_lecture`), keeping the pipeline body and its status/progress writes and temp-workdir cleanup intact.
- New config: `REDIS_URL` and `TASK_ALWAYS_EAGER`. In local dev / tests `TASK_ALWAYS_EAGER=true` runs the task **inline** (no broker, no worker) so zero extra infrastructure is required and the suite stays hermetic.
- `/api/health` reports async mode (inline vs. celery), broker presence, and cache presence.
- Deploy: a Redis instance and a worker service are added to the Render blueprint.
- **Known constraint (not a behavior change):** uploads are saved to a local temp workdir, so a separate worker host needs shared upload storage; documented for a follow-up.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `lecture-ingestion`: the requirement for how an accepted upload is processed changes from "in-process background task" to "enqueued to a durable task queue and processed by a worker pool, with eager/inline execution in dev/test." The 202-accept-then-poll contract is preserved.
- `configuration-and-health`: new `REDIS_URL` / `TASK_ALWAYS_EAGER` settings and the `async` block surfaced by `/api/health`.

## Impact

- Code: `backend/app/worker.py` (new), `backend/app/tasks.py` (new), `backend/app/ingest.py` (enqueue instead of `bg.add_task`), `backend/app/api/lectures.py` + `backend/app/web.py` (drop `BackgroundTasks` param), `backend/app/config.py` (settings + `active_async()`), `backend/app/main.py` (health).
- Dependencies: `celery[redis]`, `redis` (prod); `fakeredis` (test).
- Infra: `render.yaml` gains a `redis` instance and a `worker` service.
- Contract preserved: clients still POST → 202 → poll `GET /api/lectures/{id}` until `ready`/`failed`.
