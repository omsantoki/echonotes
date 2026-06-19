## MODIFIED Requirements

### Requirement: Create lecture in processing state and launch background pipeline

The system SHALL, on a valid upload, write the audio and slides into a private temporary workspace, create a `Lecture` record with status `processing` and an initial `Queued…` progress message, **enqueue the pipeline onto the asynchronous task queue** (the `process_lecture` Celery task) with the lecture id, course id, audio path, slides path, and workspace path, and respond with HTTP 202 carrying the new `lecture_id` and a `processing` status — returning before the pipeline completes.

#### Scenario: Valid upload accepted

- **WHEN** a valid, owner-scoped multipart upload is received
- **THEN** the system SHALL persist the audio and slides to a freshly created temp workspace
- **AND** SHALL create a `Lecture` with `status` = `processing` and `progress` = `Queued…`
- **AND** SHALL respond HTTP 202 with `{ "lecture_id": <id>, "status": "processing" }`

#### Scenario: Pipeline enqueued, not run inline

- **WHEN** the lecture record has been created
- **THEN** the system SHALL dispatch the `process_lecture` task (via `.delay`) with the lecture id, course id, audio path, slides path, and workspace path
- **AND** SHALL return the HTTP 202 response without executing the pipeline in the request handler

## ADDED Requirements

### Requirement: Durable asynchronous pipeline processing

The system SHALL process the enqueued lecture pipeline on a Celery worker backed by Redis (broker + result backend), wrapping the unchanged `run_pipeline` work function. The task SHALL be configured for durability — late acknowledgement so an in-flight task is re-delivered if a worker dies, and automatic retry with backoff on transient errors (`ConnectionError`, `TimeoutError`) up to a bounded number of attempts. A final, non-transient failure SHALL still drive the lecture to the `failed` state via the pipeline's own error handling.

#### Scenario: Worker executes the pipeline

- **WHEN** the `process_lecture` task is delivered to a worker
- **THEN** the worker SHALL invoke `run_pipeline` with the task's arguments, which updates the lecture's progress/status and removes the temp workspace exactly as in the synchronous path

#### Scenario: Transient failure is retried

- **WHEN** the task raises a transient error (`ConnectionError` or `TimeoutError`)
- **THEN** Celery SHALL retry the task with backoff up to the configured maximum before giving up

#### Scenario: Eager inline execution in dev/test

- **WHEN** `task_always_eager` is true (default for local dev and the test suite, no `REDIS_URL` required)
- **THEN** dispatching the task SHALL run `run_pipeline` inline in the calling process, preserving the 202-then-poll contract without a broker or worker
