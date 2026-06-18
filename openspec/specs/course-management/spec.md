# course-management

## Purpose

Provides the JSON API for courses under `/api/courses`: create a course, list the
caller's courses, fetch a course's detail (with its lectures), run cross-lecture search
within a course, and delete a course. Every route requires an authenticated owner and is
scoped to that owner so a user only ever sees their own courses (feature 002, Art. X).

## Requirements

### Requirement: Authenticated owner required for every course route

The system SHALL require a valid `Authorization: Bearer <jwt>` session token on every
`/api/courses` route via the `get_current_user` dependency, and SHALL reject any request
without a valid token with HTTP 401 before performing any course operation.

#### Scenario: Request without a valid bearer token

- **WHEN** a request to any `/api/courses` route is made with a missing, malformed,
  invalid, or expired token, or a token for a user that no longer exists
- **THEN** the system responds with HTTP 401 and the error code `unauthorized`
- **AND** no course is created, read, searched, or deleted

#### Scenario: Authenticated request resolves the owner

- **WHEN** a request carries a valid bearer token for an existing user
- **THEN** the system resolves the user and passes `user["id"]` as the `owner_id` to the
  storage layer for the operation

### Requirement: Create a course

The system SHALL create a course owned by the authenticated caller from a JSON body
containing `name`, and SHALL respond with HTTP 201 and the new course's `id`, `name`,
and ISO-8601 `created_at`.

#### Scenario: Create a course with a name

- **WHEN** an authenticated user POSTs `{"name": "<name>"}` to `/api/courses`
- **THEN** the system creates a `Course` with that name and `owner_id` set to the caller
- **AND** responds with HTTP 201 and a body containing `id`, `name`, and `created_at`
  (an ISO-8601 timestamp)

### Requirement: List the caller's courses

The system SHALL return only the courses owned by the authenticated caller, each
represented by its `id`, `name`, and `lecture_count`.

#### Scenario: List courses for the caller

- **WHEN** an authenticated user GETs `/api/courses`
- **THEN** the system returns a JSON array of the caller's courses only
- **AND** each entry contains `id`, `name`, and `lecture_count` (defaulting to 0 when
  absent)

#### Scenario: Another owner's courses are excluded

- **WHEN** courses exist that are owned by a different user
- **THEN** those courses do not appear in the caller's list response

### Requirement: Fetch course detail with its lectures

The system SHALL return a single owned course's `id`, `name`, and a `lectures` array
(each lecture with `id`, `title`, `date`, and `status`), and SHALL return HTTP 404 with
code `course_not_found` when the course does not exist or is not owned by the caller.

#### Scenario: Fetch an owned course

- **WHEN** an authenticated user GETs `/api/courses/{course_id}` for a course they own
- **THEN** the system returns `id`, `name`, and a `lectures` array
- **AND** each lecture entry contains `id`, `title`, `date`, and `status`

#### Scenario: Fetch a non-existent or non-owned course

- **WHEN** an authenticated user GETs `/api/courses/{course_id}` for a course that does
  not exist or is owned by another user
- **THEN** the system responds with HTTP 404 and the error code `course_not_found`
- **AND** the response does not distinguish a non-owned course from a missing one

### Requirement: Cross-lecture search within a course

The system SHALL perform cross-lecture retrieval within an owned course for a query
string `q`, returning the matching note segments, and SHALL enforce ownership before
searching by returning HTTP 404 with code `course_not_found` for a non-existent or
non-owned course.

#### Scenario: Search an owned course

- **WHEN** an authenticated user GETs `/api/courses/{course_id}/search?q=<query>` for a
  course they own
- **THEN** the system returns a body with the echoed `query` and a `results` array of
  matching note segments (each carrying `lecture_id`, `lecture_title`, `topic`, `text`,
  and `source_type`)

#### Scenario: Empty query returns no results

- **WHEN** an authenticated user searches an owned course with a missing or blank `q`
- **THEN** the system returns `results` as an empty array

#### Scenario: Search a non-existent or non-owned course

- **WHEN** an authenticated user searches a course that does not exist or is owned by
  another user
- **THEN** the system responds with HTTP 404 and the error code `course_not_found`

### Requirement: Delete a course and cascade its lectures

The system SHALL delete an owned course and cascade-delete all of its lectures (and their
notes/diagram assets), responding with HTTP 204, and SHALL return HTTP 404 with code
`course_not_found` when the course does not exist or is not owned by the caller.

#### Scenario: Delete an owned course

- **WHEN** an authenticated user DELETEs `/api/courses/{course_id}` for a course they own
- **THEN** the system deletes the course and cascade-deletes its lectures
- **AND** responds with HTTP 204 and no body

#### Scenario: Delete a non-existent or non-owned course

- **WHEN** an authenticated user DELETEs a course that does not exist or is owned by
  another user
- **THEN** the system responds with HTTP 404 and the error code `course_not_found`

## Known deviations

- Ownership scoping is enforced in the storage/registry layer, not in `courses.py`; the
  route handlers only pass `user["id"]` as `owner_id`. The detail and search routes call
  `_require_owned_course`, which relies on `store.get_course(course_id, owner_id=...)`
  returning `None` for non-owned courses to produce the 404.
- The search route declares `q` with a default of `""`, so a request omitting the query
  parameter is valid and yields an empty `results` array (the empty/blank query is
  short-circuited inside `retrieve.search`).
- `list_lectures(course_id)` in the detail route is not itself owner-scoped; ownership is
  established by the preceding `_require_owned_course` check on the course, after which the
  course's lectures are listed unconditionally.
- The delete cascade checks ownership once at the course level, then deletes each child
  lecture without re-passing an `owner_id`; the cascade is best-effort (vector-store delete
  failures are swallowed) per the underlying `store.delete_lecture` implementation.
- `lecture_count` on list entries comes from the registry backend (computed by counting
  lectures in the JSON backend); the route falls back to `0` via `c.get("lecture_count", 0)`
  if the backend omits it.
