# lecture-ingestion

## Purpose

Accept a lecture's audio recording and slide PDF as a multipart upload, validate them, create a `Lecture` record in the `processing` state, and launch a background pipeline that turns the inputs into a merged, source-labeled study document. The capability also guarantees that raw audio is discarded after transcription and that no upload survives the run (Constitution Art. IV).
## Requirements
### Requirement: Validated multipart upload

The system SHALL accept a multipart upload consisting of `course_id`, `title`, an `audio` file, and a `slides` file, and SHALL reject the request when the target course is not owned by the caller, when the audio file extension is not a recognized audio type, when the slides file is not a `.pdf`, or when any uploaded file exceeds the 500 MB size guard.

#### Scenario: Audio with an unsupported extension

- **WHEN** a request supplies an `audio` file whose extension is not one of the recognized audio extensions (`.mp3`, `.m4a`, `.wav`, `.flac`, `.ogg`, `.webm`, `.mp4`, `.mpeg`, `.mpga`, `.aac`)
- **THEN** the system SHALL respond with HTTP 400 and a `bad_upload` error code
- **AND** no `Lecture` record SHALL be created

#### Scenario: Slides that are not a PDF

- **WHEN** a request supplies a `slides` file whose extension is not `.pdf`
- **THEN** the system SHALL respond with HTTP 400 and a `bad_upload` error code

#### Scenario: Upload exceeds the size guard

- **WHEN** an uploaded file streams more than 500 MB of data
- **THEN** the system SHALL respond with HTTP 413 and a `file_too_large` error code

#### Scenario: Course not owned by the caller

- **WHEN** the `course_id` does not resolve to a course owned by the authenticated caller
- **THEN** the system SHALL respond with HTTP 404 and a `course_not_found` error code, never HTTP 403

### Requirement: Authenticated, owner-scoped ingestion

The system SHALL require an authenticated user for the upload endpoint and SHALL scope the course ownership check to that user's id, so a caller can only ingest into a course they own.

#### Scenario: Unauthenticated upload

- **WHEN** the upload endpoint is called without a valid session
- **THEN** the system SHALL reject the request via the `get_current_user` dependency rather than creating a lecture

#### Scenario: Authenticated upload into an owned course

- **WHEN** an authenticated caller uploads to a course whose owner is that caller
- **THEN** the system SHALL proceed to create the lecture and launch the pipeline using the caller's id as the owner scope

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

### Requirement: Ordered pipeline stage orchestration

The background pipeline SHALL execute its stages in a fixed order — transcribe, extract slides (text + filtered images), align spoken segments to slide sections, describe and persist diagrams, compose merged and refined note chunks, embed the chunk texts, and persist the chunks per course — updating the lecture's human-readable `progress` field as it advances.

#### Scenario: Stages run in order with progress updates

- **WHEN** the pipeline runs for a lecture
- **THEN** the system SHALL transcribe the audio, then extract and image-filter the slides, then align segments to sections, then describe/persist diagrams, then compose refined note chunks, then embed those chunks, then persist them
- **AND** SHALL update the lecture `progress` message at each stage (e.g. `Transcribing audio…`, `Reading slides…`, `Aligning what was said to the slides…`, `Describing diagrams…`, `Composing your merged notes…`, `Saving notes…`)

#### Scenario: No content produced

- **WHEN** composition yields zero note chunks
- **THEN** the system SHALL raise an error that drives the lecture into the `failed` state rather than persisting an empty document

### Requirement: Lecture status transitions

The system SHALL transition a lecture from `processing` to `ready` only after chunks are embedded and persisted, and SHALL transition it to `failed` with a `Failed: <reason>` progress message if any stage raises an exception, without crashing the background worker.

#### Scenario: Successful run reaches ready

- **WHEN** the pipeline completes all stages without error
- **THEN** the system SHALL set the lecture `status` to `ready` and `progress` to `Ready.`

#### Scenario: Failure during any stage

- **WHEN** any pipeline stage raises an exception
- **THEN** the system SHALL set the lecture `status` to `failed` and `progress` to a message beginning with `Failed:`
- **AND** the background worker SHALL not crash

### Requirement: Raw audio discarded after transcription

The system SHALL delete the raw audio file immediately after transcription finishes and SHALL remove the entire temporary workspace (audio and slides) when the pipeline ends, including on failure, so no uploaded recording is ever persisted (Constitution Art. IV).

#### Scenario: Audio deleted right after transcription

- **WHEN** transcription of the audio file completes
- **THEN** the system SHALL delete the raw audio file before continuing to the next stage

#### Scenario: Workspace removed even on failure

- **WHEN** the pipeline finishes, whether it succeeds or fails
- **THEN** the system SHALL remove the entire temporary workspace directory (audio and slides) in a `finally` step that ignores deletion errors

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

## Known deviations

- The upload endpoint accepts `title` as a required form field, but ingestion still defaults a blank title to `"Untitled lecture"`; the two layers disagree on whether title can be empty.
- The pipeline's documented sequence in the module docstring lists "place diagrams" after refine, while the actual code describes/persists diagrams before composing chunks and weaves diagram captions into composition. The docstring ordering is stale relative to the implementation.
- `LectureStatus` defines an `uploaded` value and it is the model default, but the ingestion path never uses it — lectures are created directly in `processing`. The `uploaded` state is effectively dead for this capability.
- Cross-lecture linking (`_link_prior_lectures`) runs after persistence as best-effort work that swallows all exceptions, so a linking failure is silent and never affects lecture status.
- Diagram description depends on a vision model; when none is available, `describe_image` returns no description and the chunk falls back to a plain caption (`Diagram from "<topic>".`). This is a graceful stub rather than a guaranteed-described-diagram behavior.
- File-type validation is by filename extension only; there is no content/MIME sniffing, so a misnamed file can pass or fail validation based purely on its extension.
