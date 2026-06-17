# persistence

## Purpose

Provide the single storage facade (`app/store.py`) that the rest of EchoNotes imports for all persistence, over three pluggable backends selected at runtime from configuration: a registry (JSON file locally / Postgres in production) for structural rows, a vector store (local or remote Chroma / Qdrant) for embedded NoteChunks, and object storage (local disk / S3-R2) for preserved diagram images. The facade owns cross-backend validation, the document-assembly shape, owner scoping, and the multi-store delete cascade so no individual backend can diverge on them.

## Requirements

### Requirement: Configuration-selected pluggable backends

The system SHALL select each of the three storage backends lazily from configuration so that an all-blank (local) install needs no cloud SDKs: the vector backend is `QdrantVectors` when `qdrant_url` is set, else `RemoteChromaVectors` when `chroma_http_url` is set, else `LocalChromaVectors`; the registry backend is `PostgresRegistry` when `database_url` is set, else `JsonRegistry`; and the object backend is `S3Objects` when `s3_bucket` is set, else `LocalObjects`.

#### Scenario: All env vars blank selects local backends

- **WHEN** the facade resolves backends with `qdrant_url`, `chroma_http_url`, `database_url`, and `s3_bucket` all blank
- **THEN** it selects `LocalChromaVectors`, `JsonRegistry`, and `LocalObjects`
- **AND** the cloud SDKs (qdrant_client, psycopg, boto3) are not imported, because backend modules are imported lazily inside the `_vectors`/`_registry`/`_objects` selectors

#### Scenario: Cloud env vars select managed backends

- **WHEN** `database_url`, `s3_bucket`, and `qdrant_url` are set
- **THEN** the facade selects `PostgresRegistry`, `S3Objects`, and `QdrantVectors` respectively
- **AND** each selector result is memoized via `lru_cache` so the backend is constructed once per process

### Requirement: NoteChunk validation before vector storage

The system SHALL enforce, in the facade's `add_chunks`, that every persisted NoteChunk has a non-empty text, an embedding, and both a `source_type` and a `reason`, dropping blank-text chunks and rejecting the rest with a `ValueError`, so that every vector backend uniformly upholds the source-label / explainability / single-embedding invariants.

#### Scenario: Blank-text chunks are dropped

- **WHEN** `add_chunks` receives chunks whose `text` is empty or whitespace
- **THEN** those chunks are filtered out before storage
- **AND** if no chunks remain it returns without calling the vector backend

#### Scenario: Missing embedding is rejected

- **WHEN** `add_chunks` receives a chunk whose `embedding` is `None`
- **THEN** it raises a `ValueError` naming the chunk id and citing the single-embedding requirement

#### Scenario: Missing source_type or reason is rejected

- **WHEN** `add_chunks` receives a chunk missing `source_type` or `reason`
- **THEN** it raises a `ValueError` naming the chunk id and citing the source-label / explainability requirement

#### Scenario: Valid chunks reach the vector backend

- **WHEN** `add_chunks` receives chunks that all pass validation
- **THEN** it calls the selected vector backend's `add` with those chunks

### Requirement: Per-course similarity search with self-exclusion

The system SHALL run similarity search scoped to a single `course_id` through the vector backend's `query`, optionally excluding one lecture's own chunks via `exclude_lecture_id`, and SHALL return results carrying a cosine `distance` (smaller = closer) so retrieval logic can convert it to similarity uniformly across backends.

#### Scenario: Course-scoped query

- **WHEN** `query(course_id, embedding, n)` is called
- **THEN** results are filtered to that `course_id` and limited to `n` matches
- **AND** each result dict carries `id`, `text`, `metadata`, and `distance`

#### Scenario: Excluding a lecture's own chunks

- **WHEN** `query` is called with `exclude_lecture_id` set
- **THEN** chunks belonging to that lecture are excluded from the results

#### Scenario: Qdrant normalizes similarity to distance

- **WHEN** the Qdrant backend returns a per-point cosine `score` (similarity, higher = closer)
- **THEN** it reports `distance = 1.0 - score` so callers see the same distance convention as the Chroma backends

### Requirement: Document assembly grouped by topic

The system SHALL assemble a lecture's stored chunks into a topic-ordered document via `assemble_document`, grouping segments by `topic` in document order, carrying each segment's `source_type`, `text`, `reason`, and `confidence`, flagging spoken-only segments, resolving any `diagram_ref` to a stored image URL, and attaching per-topic cross-lecture `builds_on` links when present.

#### Scenario: Segments grouped by topic in order

- **WHEN** `assemble_document(lecture_id)` is called
- **THEN** it lists the lecture's chunks (ordered by `order`) and groups them under their `topic`, in first-seen topic order
- **AND** chunks without a topic are grouped under the default topic `"Notes"`

#### Scenario: Spoken-only emphasis flag

- **WHEN** a segment's `source_type` is `spoken` and its `reason` starts with the spoken-only marker (`★ Spoken-only`)
- **THEN** that segment's `spoken_only` flag is `True`

#### Scenario: Diagram reference resolved to an image URL

- **WHEN** a segment carries a `diagram_ref`
- **THEN** the facade looks up the diagram asset and sets `image_ref` to the asset's stored image location (or `None` if the asset is missing)

#### Scenario: Cross-lecture builds-on links attached

- **WHEN** the lecture record carries `links` for a topic present in the document
- **THEN** that topic gains a `builds_on` entry from the lecture's stored links

### Requirement: Owner-scoped registry reads and deletes

The system SHALL scope course and lecture reads, lists, and deletes by `owner_id` when one is supplied, enforcing the filter inside the registry backend so a non-owner receives the same "not found" (`None` / `False`) as a missing record, while `owner_id=None` is the internal/system path that applies no owner filter.

#### Scenario: Non-owner read returns not found

- **WHEN** `get_course(course_id, owner_id)` is called with an `owner_id` that does not match the course's `owner_id`
- **THEN** the registry returns `None`, indistinguishable from a missing course (no existence leak)

#### Scenario: Lecture ownership resolved through its course

- **WHEN** `get_lecture(lecture_id, owner_id)` is called
- **THEN** ownership is checked via the lecture's parent course (JSON: `_owns_lecture`; Postgres: a JOIN on `courses.owner_id`)
- **AND** a non-owner gets `None`

#### Scenario: System path bypasses the owner filter

- **WHEN** a registry read/list is called with `owner_id=None` (e.g. the pipeline or the startup recovery scan via `list_all_lectures`)
- **THEN** no owner filter is applied and rows for all owners are visible

#### Scenario: List counts lectures per course

- **WHEN** `list_courses(owner_id)` is called
- **THEN** each returned course carries a `lecture_count` of its lectures

### Requirement: Cross-store delete cascade

The system SHALL orchestrate deletes that span all three backends in the facade: `delete_lecture` removes the registry rows, the lecture's vectors, and its stored diagram images; `delete_course` confirms ownership once then cascade-deletes each of its lectures and finally the course row. Both return `False` when the target is absent or not owned by the given `owner_id`.

#### Scenario: Deleting a lecture cascades to vectors and assets

- **WHEN** `delete_lecture(lecture_id, owner_id)` is called for an owned, existing lecture
- **THEN** the registry rows are deleted first, then the lecture's vectors are deleted (best-effort, swallowing backend errors), then its stored diagram images are deleted
- **AND** it returns `True`

#### Scenario: Deleting an absent or non-owned lecture is a no-op

- **WHEN** `delete_lecture` is called for a lecture that does not exist or is not owned by `owner_id`
- **THEN** the registry delete returns `False` and the facade returns `False` without touching the vector or object backends

#### Scenario: Deleting a course cascades to its lectures

- **WHEN** `delete_course(course_id, owner_id)` is called for an owned course
- **THEN** ownership is confirmed once, every lecture id under the course is deleted via the lecture cascade, and the course row is removed
- **AND** it returns `True`; a non-owned or missing course returns `False` with no cascade

### Requirement: Hashed-only auth credential persistence

The system SHALL persist users and short-lived auth tokens through the registry, storing only hashed secrets (never plaintext passwords, OTPs, or tokens), and SHALL support single-use token semantics: finding the newest unused token for a user+kind, bumping a token's attempts/used flags, and invalidating all prior tokens of a kind for a user.

#### Scenario: User identity is email-keyed and hashed

- **WHEN** a `User` is created and later looked up by email
- **THEN** the lookup normalizes the email to lowercase before matching
- **AND** the stored record holds `password_hash` (or `None` for Google-only accounts), never a plaintext password

#### Scenario: Active token is the newest unused for a user+kind

- **WHEN** `find_auth_token(kind, user_id=...)` is called
- **THEN** it returns the most recently created token of that kind for the user that is still unused, or `None` if none exists

#### Scenario: Token lookup by hash

- **WHEN** `find_auth_token(kind, token_hash=...)` is called
- **THEN** it returns the newest matching token by hash for that kind (Postgres returns `None` when neither `user_id` nor `token_hash` is given)

#### Scenario: Invalidating prior tokens prevents replay

- **WHEN** `invalidate_auth_tokens(user_id, kind)` is called
- **THEN** every token of that kind for the user is marked `used`, so an old OTP or reset link can no longer be consumed

### Requirement: Preserved diagram image object storage

The system SHALL store preserved diagram images through the object backend, returning a reference suitable for the document's `image_ref` — a root-relative `/assets/{lecture_id}/{asset_id}.{ext}` path locally, or an absolute public URL in production — and SHALL be able to read those bytes back (for the description backfill) and delete all of a lecture's assets on cascade.

#### Scenario: Local save returns an /assets path

- **WHEN** `save_diagram_image(lecture_id, asset_id, ext, data)` is called on the local backend
- **THEN** the bytes are written under `DATA_DIR/assets/{lecture_id}/` and a `/assets/{lecture_id}/{asset_id}.{ext}` path is returned (defaulting the extension to `png`)

#### Scenario: S3/R2 save returns an absolute URL

- **WHEN** `save_diagram_image` is called on the S3 backend
- **THEN** the object is uploaded to `assets/{lecture_id}/{asset_id}.{ext}` with a content type inferred from the extension
- **AND** the returned reference is `{s3_public_base_url}/assets/{lecture_id}/{asset_id}.{ext}`

#### Scenario: Reading back stored bytes

- **WHEN** `read_diagram_bytes(asset)` is called
- **THEN** the local backend resolves the asset's `image_ref` under `DATA_DIR` and returns its bytes (or `None` if absent), and the S3 backend reconstructs the key and returns the object bytes (or `None` on any error)

#### Scenario: Lecture asset deletion

- **WHEN** `delete_lecture_assets(lecture_id)` is called
- **THEN** the local backend recursively removes `DATA_DIR/assets/{lecture_id}`, and the S3 backend lists and deletes all objects under the `assets/{lecture_id}/` prefix

## Known deviations

- Raw audio and source PDFs are deliberately never persisted by this capability — there is no Audio entity in the data model (Constitution Art. IV); discarding them lives in the pipeline, not in `store.py`.
- The `JsonRegistry` backend is single-process only: it does read-modify-write of `registry.json` under an in-process `threading.Lock`, so it is not safe for multi-instance deploys (production must use `PostgresRegistry`, whose Postgres schema is created out-of-band by `scripts/init_db.py` and is not provisioned by this capability).
- The delete cascade is not transactional across backends: `delete_lecture` deletes registry rows first, then best-effort deletes vectors (swallowing any exception with a bare `except: pass`) and object assets. A vector- or object-store failure can leave orphaned vectors or images with no registry row pointing at them, and there is no reconciliation pass.
- Owner scoping differs by backend internals but matches at the contract: JSON walks course/lecture dicts in Python under the lock; Postgres pushes the filter into SQL (`WHERE owner_id = %s` / a JOIN) and relies on an `ON DELETE CASCADE` FK to remove diagram rows, whereas the JSON backend deletes diagram rows explicitly inside `delete_lecture_rows`.
- `Course.owner_id` is nullable (`None`) to accommodate pre-002 legacy rows; such rows are only reachable via the `owner_id=None` system path, so a logged-in user never sees an unowned course through the normal owner-scoped routes.
- The Postgres `create_course`/`create_lecture`/`create_diagram` use `ON CONFLICT (id) DO UPDATE` (upsert), so re-creating with an existing id silently overwrites fields rather than erroring; the JSON backend likewise overwrites the dict entry. There is no create-vs-update distinction at this layer.
- `reason` is persisted in the vector metadata even though the data-model's mandated metadata set does not include it; the facade keeps it there (per the `metadata()` comment) because the API contract returns it per block and only notes are persisted.
