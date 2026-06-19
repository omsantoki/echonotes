<!-- Code is already implemented and tested; boxes are checked to reflect completed work. -->

## 1. Dependencies

- [x] 1.1 Add `celery[redis]` and `redis` to `backend/requirements.txt`
- [x] 1.2 Add `fakeredis` to `backend/requirements-test.txt`

## 2. Celery app + task

- [x] 2.1 Create `backend/app/worker.py` (Celery app; broker/result = `redis_url`; `task_always_eager`, `acks_late`, `prefetch=1`)
- [x] 2.2 Create `backend/app/tasks.py` with `process_lecture` wrapping `run_pipeline` (retries + backoff on transient errors)

## 3. Enqueue on upload

- [x] 3.1 Replace `bg.add_task(run_pipeline, ...)` with `process_lecture.delay(...)` in `backend/app/ingest.py`; drop the `BackgroundTasks` param
- [x] 3.2 Drop the `BackgroundTasks` argument from `create_lecture` (`backend/app/api/lectures.py`) and `web_create_lecture` (`backend/app/web.py`)

## 4. Config + health

- [x] 4.1 Add `redis_url` and `task_always_eager` settings to `backend/app/config.py`
- [x] 4.2 Add `active_async()` helper and surface the `async` block in `GET /api/health`
- [x] 4.3 Document the new env vars in `backend/.env.example`

## 5. Deploy

- [x] 5.1 Add a `redis` instance and a `celery worker` service to `render.yaml`; wire `REDIS_URL` + `TASK_ALWAYS_EAGER` on web and worker, with the shared-upload-storage caveat documented

## 6. Tests

- [x] 6.1 Test that upload enqueues the task (mocked) and returns 202 with `processing` status (`backend/tests/test_async_qa.py`)
- [x] 6.2 Confirm the full backend suite stays green in eager mode (no broker)

## 7. Manual verification (broker mode)

- [ ] 7.1 With `REDIS_URL` set and `TASK_ALWAYS_EAGER=false`, run a worker and upload the demo lecture: API returns 202 instantly, worker log shows `process_lecture`, status polls `processing → ready`; killing/restarting the worker mid-run re-delivers the task
