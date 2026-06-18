# lecture-management

## Purpose

Provides the authenticated JSON API for the lifecycle of a lecture under `/api/lectures`: ingesting an audio + slides pair to launch the merge pipeline, reading processing status or the assembled merged document, exporting that document as Markdown or HTML, and deleting a lecture together with its derived data. Every route is owner-scoped so a caller only ever acts on lectures belonging to courses they own.

## Requirements

### Requirement: Authenticated access to all lecture routes

The system SHALL require an authenticated session for every lecture route (create, get, export, delete) via the `get_current_user` dependency, and SHALL reject unauthenticated requests with HTTP 401 (`code: "unauthorized"`).

#### Scenario: Request without a valid session

- **WHEN** any `/api/lectures` route is called without a valid `Authorization` bearer token (missing, malformed, or for a user that no longer exists)
- **THEN** the system responds with HTTP 401 and detail `code: "unauthorized"`
- **AND** does not perform the requested lecture action

### Requirement: Ingest a lecture into an owned course

The system SHALL accept a multipart `POST /api/lectures` with `course_id`, `title`, an `audio` file, and a `slides` file, and SHALL launch the merge pipeline as a background task while returning HTTP 202 with the new `lecture_id` and `status: "processing"`. The audio and slides SHALL be written to a private temp workspace before the pipeline runs.

#### Scenario: Valid upload to an owned course

- **WHEN** an authenticated user posts a `course_id` they own with `title`, a supported `audio` file, and a `.pdf` `slides` file
- **THEN** the system creates a `Lecture` with status `processing` and progress `"Queued…"`, saves both uploads to a temp workspace, and schedules the pipeline as a background task
- **AND** responds with HTTP 202 and body `{ "lecture_id": <id>, "status": "processing" }`

#### Scenario: Upload to a course the caller does not own or that is missing

- **WHEN** an authenticated user posts to a `course_id` that does not exist or is owned by another user
- **THEN** the system responds with HTTP 404 and detail `code: "course_not_found"`
- **AND** does not create a lecture or launch the pipeline

### Requirement: Validate uploaded file types and size

The system SHALL reject ingest uploads whose audio extension is not one of the allowed audio types or whose slides file is not a `.pdf`, and SHALL reject any upload that exceeds the 500 MB size guard rail.

#### Scenario: Unsupported file type

- **WHEN** the `audio` file has an extension outside the allowed set (`.mp3 .m4a .wav .flac .ogg .webm .mp4 .mpeg .mpga .aac`) or the `slides` file is not a `.pdf`
- **THEN** the system responds with HTTP 400 and detail `code: "bad_upload"`

#### Scenario: Upload exceeds size limit

- **WHEN** an uploaded file streams past 500 MB
- **THEN** the system responds with HTTP 413 and detail `code: "file_too_large"`

### Requirement: Report lecture status while processing

The system SHALL return the lecture's current status and progress for an owned lecture that is not yet `ready`, without returning a document.

#### Scenario: Fetch a not-yet-ready lecture

- **WHEN** an authenticated owner calls `GET /api/lectures/{lecture_id}` for a lecture whose status is not `ready`
- **THEN** the system responds with HTTP 200 and body `{ "id", "status", "progress" }` reflecting the stored status and progress string

### Requirement: Return the assembled merged document when ready

The system SHALL return the assembled topic-organized merged document for an owned lecture once its status is `ready`, including the lecture title.

#### Scenario: Fetch a ready lecture

- **WHEN** an authenticated owner calls `GET /api/lectures/{lecture_id}` for a lecture whose status is `ready`
- **THEN** the system responds with HTTP 200 and body `{ "id", "status": "ready", "title", "document" }`
- **AND** `document` contains the topic-grouped segments built by `assemble_document`, each segment carrying its `source_type`, `text`, `reason`, `confidence`, `spoken_only` flag, and any `diagram_ref`/`image_ref`

### Requirement: Export a ready lecture as Markdown or HTML

The system SHALL export an owned, ready lecture as a downloadable file in either Markdown (`format=md`, default) or HTML (`format=html`), rejecting any other format and rejecting export before the lecture is ready.

#### Scenario: Export as Markdown or HTML

- **WHEN** an authenticated owner calls `GET /api/lectures/{lecture_id}/export` with `format=md` (or omitted) or `format=html` for a `ready` lecture
- **THEN** the system responds with HTTP 200, the rendered document body, the matching media type (`text/markdown` or `text/html`), and a `Content-Disposition: attachment` header with a sanitized filename derived from the title

#### Scenario: Export before ready

- **WHEN** an authenticated owner requests export of a lecture whose status is not `ready`
- **THEN** the system responds with HTTP 409 and detail `code: "not_ready"`

#### Scenario: Unsupported export format

- **WHEN** the `format` query parameter is neither `md` nor `html`
- **THEN** the system responds with HTTP 400 and detail `code: "bad_format"`

### Requirement: Delete an owned lecture and its derived data

The system SHALL delete an owned lecture along with its NoteChunk vectors, its preserved diagram images, and its registry rows, returning HTTP 204 on success. Deletion SHALL be owner-scoped so that a lecture the caller does not own behaves identically to a missing one.

#### Scenario: Delete an owned lecture

- **WHEN** an authenticated owner calls `DELETE /api/lectures/{lecture_id}` for a lecture they own
- **THEN** the system removes the lecture's registry rows, its vector chunks (best-effort), and its preserved diagram image assets
- **AND** responds with HTTP 204 (no body)

#### Scenario: Delete a non-owned or missing lecture

- **WHEN** an authenticated user calls `DELETE /api/lectures/{lecture_id}` for a lecture that does not exist or is owned by another user
- **THEN** the system responds with HTTP 404 and detail `code: "lecture_not_found"`
- **AND** never responds with 403

### Requirement: Treat non-owned and missing lectures as not found on read and export

The system SHALL resolve `get_lecture` with the caller's owner scope on the status/document and export routes, returning HTTP 404 (`code: "lecture_not_found"`) for any lecture the caller does not own or that does not exist, rather than 403.

#### Scenario: Read or export a lecture the caller does not own

- **WHEN** an authenticated user calls `GET /api/lectures/{lecture_id}` or `GET /api/lectures/{lecture_id}/export` for a lecture that does not exist or is owned by another user
- **THEN** the system responds with HTTP 404 and detail `code: "lecture_not_found"`
- **AND** does not disclose the lecture's status, document, or contents

## Known deviations

- The status/document route reads `lec.get("progress", "")` defaulting to an empty string, but on the ingest path progress is initialized to `"Queued…"`, so the empty-string default only surfaces for records lacking a progress value.
- Vector deletion during `delete_lecture` is best-effort: failures from the vector store are caught and swallowed (`except Exception: pass`), so the registry rows and diagram assets are still removed even if vector cleanup fails, potentially leaving orphaned vectors.
- `assemble_document` also attaches a `builds_on` field per topic from stored cross-lecture links; this is a Stretch feature (T041) and depends on links having been persisted by the pipeline.
- Filename sanitization (`_safe_filename`) strips characters that are not alphanumeric, space, hyphen, or underscore, replacing them with `_`, and falls back to `"lecture"` if the resulting base is empty.
