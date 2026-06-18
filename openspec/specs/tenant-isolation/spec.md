# tenant-isolation

## Purpose

Ensure a user only ever sees their own data (Constitution Article X). Every JSON data route requires a valid session or returns 401; the per-owner filter is pushed down into the storage layer (not just checked in the route); a request for a resource the caller does not own returns the SAME 404 as a missing resource (never 403), so existence is never leaked. The public landing/console surface is governed separately, and pre-existing ownerless data is migrated to a documented bootstrap owner rather than dropped.

## Requirements

### Requirement: Data routes require an authenticated session

The system SHALL require a valid `Authorization: Bearer <jwt>` session token on every course and lecture data route, resolving it to the owning user via `get_current_user`, and SHALL reject any request without a usable session with HTTP 401 (`code: "unauthorized"`) before any data is read.

#### Scenario: Missing or malformed Authorization header is rejected

- **WHEN** a request hits a course or lecture data route with no `Authorization` header, or a header that does not start with `bearer ` (case-insensitive)
- **THEN** `get_current_user` raises HTTP 401 with detail `{code: "unauthorized", message: "Authentication required."}`
- **AND** no course or lecture data is read or returned

#### Scenario: Invalid, expired, or orphaned token is rejected

- **WHEN** the bearer token fails `decode_session_token` (invalid/expired/malformed), or decodes to a `user_id` for which `store.get_user` returns nothing
- **THEN** `get_current_user` raises HTTP 401 (`code: "unauthorized"`)
- **AND** the route handler never executes

#### Scenario: Valid session resolves to the owning user

- **WHEN** a request carries a bearer token that decodes to an existing user
- **THEN** `get_current_user` returns that user record (a dict)
- **AND** the route passes `user["id"]` to `store` as the `owner_id` for all subsequent reads, lists, and deletes

### Requirement: Owner filter enforced in the storage layer

The system SHALL apply the per-owner filter inside the registry storage backend itself when an `owner_id` is supplied, so isolation does not depend solely on a route-level check, and SHALL apply no owner filter when `owner_id` is `None` (the internal/system path).

#### Scenario: Owner-scoped read filters in the backend

- **WHEN** `store.get_course(course_id, owner_id=X)` or `store.get_lecture(lecture_id, owner_id=X)` is called
- **THEN** the JSON backend returns `None` when the stored record's `owner_id` does not equal `X`, and the Postgres backend restricts the query with `WHERE owner_id = %s` (courses) or a JOIN on the parent course's `owner_id` (lectures)
- **AND** a non-owned record is indistinguishable from a missing record at the storage boundary

#### Scenario: Lecture ownership resolved through the parent course

- **WHEN** a lecture read or delete is performed with an `owner_id`
- **THEN** ownership is decided by the parent course's `owner_id` (the JSON backend's `_owns_lecture` / the Postgres JOIN), not by a field on the lecture itself

#### Scenario: System path bypasses the owner filter

- **WHEN** a backend method is called with `owner_id=None` (e.g. startup recovery scanning `list_all_lectures`, the pipeline, or the migration script's `list_courses(owner_id=None)`)
- **THEN** no owner filter is applied and records across all owners are returned

### Requirement: Non-owned resources return 404, never 403

The system SHALL return HTTP 404 (the same `*_not_found` response used for a genuinely missing resource) when a caller requests, searches, exports, or deletes a course or lecture they do not own, and SHALL NEVER return 403 for a data resource, so the existence of another user's data is not leaked.

#### Scenario: Fetching a non-owned course returns 404

- **WHEN** an authenticated user calls `GET /api/courses/{course_id}` (or `/search`, or `DELETE`) for a course owned by a different user
- **THEN** the route raises HTTP 404 with `code: "course_not_found"`, identical to the response for a course id that does not exist
- **AND** no 403 is ever returned and no information distinguishing "not yours" from "does not exist" is disclosed

#### Scenario: Fetching a non-owned lecture returns 404

- **WHEN** an authenticated user calls `GET /api/lectures/{lecture_id}` (or `/export`, or `DELETE`) for a lecture whose parent course is owned by another user
- **THEN** the route raises HTTP 404 with `code: "lecture_not_found"`, identical to the response for a missing lecture id

#### Scenario: Owner-scoped delete returns false for non-owners

- **WHEN** `store.delete_course` or `store.delete_lecture` is called with an `owner_id` that does not own the target
- **THEN** the delete returns `False` and removes nothing, and the route translates that into a 404 (`*_not_found`)

### Requirement: Listings return only the caller's data

The system SHALL scope all listing endpoints to the authenticated caller so that a list never contains another user's resources.

#### Scenario: Course listing is owner-scoped

- **WHEN** an authenticated user calls `GET /api/courses`
- **THEN** the response contains only courses where `owner_id` equals the caller's id, as filtered by `store.list_courses(owner_id=user["id"])`
- **AND** courses owned by other users are absent from the result

### Requirement: Writes bind new resources to the caller and verify the parent

The system SHALL set the authenticated caller as the `owner_id` of any course they create, and SHALL ingest a lecture only into a course the caller owns (resolved through the storage owner filter), so a user cannot create data under another user's tenancy.

#### Scenario: Created course is owned by the caller

- **WHEN** an authenticated user calls `POST /api/courses`
- **THEN** the new `Course` is persisted with `owner_id` set to `user["id"]`

#### Scenario: Lecture ingest is owner-scoped to its course

- **WHEN** an authenticated user calls `POST /api/lectures` with a `course_id`
- **THEN** `create_and_launch_lecture` is invoked with `owner_id=user["id"]` so the lecture is only created against a course owned by that caller

### Requirement: Public landing surface stays unauthenticated; data console is owner-bound

The system SHALL keep the landing page public and SHALL NOT expose an unauthenticated multi-tenant data surface; the built-in server-rendered console operates as a single bootstrap owner and is mounted only when explicitly enabled (off in production).

#### Scenario: Server-rendered console is single-tenant and gated by config

- **WHEN** the server-rendered web console (`web.py`) is mounted (only when `enable_web_console` is true, default on for local dev, off in production via render.yaml)
- **THEN** every console read and write passes `owner_id = ensure_bootstrap_admin()["id"]`, so it is always scoped to the one bootstrap admin and never uses the unscoped all-owners path
- **AND** in production the console is not mounted, so no unauthenticated course-create or lecture-upload surface is exposed

#### Scenario: Console hides non-bootstrap resources

- **WHEN** the console renders `/courses/{course_id}` or `/lectures/{lecture_id}` for a resource not owned by the bootstrap admin
- **THEN** the page returns HTTP 404 ("Course not found." / "Lecture not found."), the same as for a missing resource

### Requirement: Legacy ownerless data migrated to a documented bootstrap owner

The system SHALL provide an idempotent migration that assigns every pre-existing ownerless ("common") course to a documented bootstrap admin (`BOOTSTRAP_ADMIN_EMAIL`) rather than dropping it, creating that admin if absent.

#### Scenario: Ownerless courses are reassigned, not deleted

- **WHEN** `scripts/migrate_add_owner.py` runs and finds courses lacking an `owner_id` (via the unscoped `list_courses(owner_id=None)`)
- **THEN** the bootstrap admin user is ensured to exist and each legacy course is re-saved in place with `owner_id` set to that admin's id, preserving its original `created_at`
- **AND** no legacy course is deleted

#### Scenario: Migration is idempotent

- **WHEN** the migration runs and every course already has an owner
- **THEN** it reports that nothing needs migrating and changes no data

## Known deviations

- The owner filter relies on every data route remembering to pass `owner_id=user["id"]` into `store`; the storage backends still accept `owner_id=None` as a deliberate unscoped/system path. There is no enforced default-deny at the store boundary, so a route that omitted the `owner_id` argument would silently read across tenants. Isolation therefore depends on both the route check and the backend filter being correct together.
- `store.delete_course` checks ownership once at the course level, then cascades into `delete_lecture(lid)` with no `owner_id` (a comment notes ownership is "already confirmed"); the per-lecture delete inside the cascade is therefore unscoped by design.
- Non-data registry lookups are not owner-scoped: `get_diagram`, `list_diagrams`, `list_chunks`, `assemble_document`, and the vector `query`/`update_chunk_text` take no `owner_id`. They are reached only after an owner-scoped lecture/course check in the route, so isolation is enforced upstream rather than on these calls themselves.
- The bootstrap admin is created password-less and email-verified; it must be claimed via the forgot-password flow (reset link printed to the server log in dev) before anyone can log in as the migrated library's owner. On Postgres deploys `scripts/init_db.py` must be run before `scripts/migrate_add_owner.py`.
- The vector store is not partitioned by owner; cross-lecture retrieval (`store.query`) is scoped only by `course_id`. Because a course is owner-scoped, this is safe only so long as a course's lectures all share that course's single owner.
