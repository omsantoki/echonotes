# cross-lecture-retrieval

## Purpose

Provide semantic search across all of a course's stored lecture note segments, returning the top few matching chunks (Strong), and link a current lecture's topics to the most similar earlier lecture in the same course as builds-on evidence (Stretch). All retrieval uses the one embedding model and is scoped to a single course, with the owning user's access enforced by the calling route.

## Requirements

### Requirement: Semantic search across a course's lectures

The system SHALL embed a text query with the one embedding model and query the vector store scoped to a single course, returning matching note segments drawn from across all of that course's lectures.

#### Scenario: Query returns matching segments across lectures

- **WHEN** `search(course_id, query)` is called with a non-empty query for a course that has stored note chunks
- **THEN** the query string is embedded via `embed_text` and passed to `store.query(course_id, ...)`
- **AND** the function returns a list of dicts, each containing `lecture_id`, `lecture_title`, `topic`, `text`, and `source_type` resolved from the matched chunk's metadata and its lecture record

#### Scenario: Empty or whitespace-only query returns nothing

- **WHEN** `search` is called with an empty string, whitespace only, or a `None`/falsy query
- **THEN** the function returns an empty list without embedding the query or touching the vector store

### Requirement: Result count capped to the top few matches

The system SHALL cap the number of returned search results at the configured `retrieve_top_n` when no explicit count is supplied.

#### Scenario: Default cap applied

- **WHEN** `search(course_id, query)` is called without an `n` argument
- **THEN** the result count `n` is taken from `get_settings().retrieve_top_n` (default 5) and used as the vector store limit

#### Scenario: Explicit count overrides the default

- **WHEN** `search(course_id, query, n=k)` is called with an explicit positive `k`
- **THEN** `k` is used as the vector store limit instead of `retrieve_top_n`

### Requirement: Each search result carries its source label

The system SHALL include the originating segment's source label (`source_type`) on every search result so callers can distinguish slides, spoken, and diagram content.

#### Scenario: Source type surfaced from metadata

- **WHEN** a search result is built for a matched chunk
- **THEN** the result's `source_type` field is populated from the chunk metadata's `source_type` value (or `None` when absent)
- **AND** `lecture_id`, `topic` are likewise read from the chunk metadata and `lecture_title` is resolved from the lecture record (empty string when the lecture is missing)

### Requirement: Link a topic to the most similar earlier lecture

The system SHALL, for each supplied current topic, find the strongest qualifying prior match in the course and return a builds-on link to that earlier lecture, excluding the current lecture's own chunks.

#### Scenario: Strongest qualifying prior match wins

- **WHEN** `find_links(course_id, topics, exclude_lecture_id=current)` is called and linking is enabled
- **THEN** each topic's combined text is embedded and queried against the course with `exclude_lecture_id=current` so a lecture never links to itself
- **AND** the first hit whose similarity (computed as `1.0 - distance`) is at least `link_min_similarity` is recorded as that topic's link, then iteration for that topic stops

#### Scenario: Link payload includes similarity evidence

- **WHEN** a topic links to an earlier lecture
- **THEN** the returned mapping is keyed by topic title and each value contains `lecture_id`, `lecture_title`, `topic`, and `similarity` rounded to three decimals

### Requirement: Apply similarity threshold and skip empty topics

The system SHALL only emit a link when a prior match clears the `link_min_similarity` threshold and SHALL skip topics with no usable text or no qualifying match.

#### Scenario: Below-threshold matches produce no link

- **WHEN** a topic's best prior hit has a similarity below `link_min_similarity`, a missing distance, or the topic text is empty/whitespace
- **THEN** no entry is added to the returned mapping for that topic

#### Scenario: Linking disabled by configuration

- **WHEN** `find_links` is called while `settings.link_lectures` is false
- **THEN** the function returns an empty mapping immediately without querying the vector store

### Requirement: Course-scoped retrieval using one embedding model

The system SHALL perform every retrieval against a single `course_id` and SHALL embed both queries and topic texts with the same one embedding model used elsewhere in the pipeline.

#### Scenario: Vector queries are confined to one course

- **WHEN** either `search` or `find_links` issues a vector lookup
- **THEN** the lookup calls `store.query(course_id, ...)` with exactly one course id and uses `embed_text` for the query embedding
- **AND** results never include chunks from a different course

## Known deviations

- Owner-scoping is not enforced inside `retrieve.py`. Neither `search` nor `find_links` accepts or passes an `owner_id`, and the underlying `store.query` filters only by `course_id` (it has no owner parameter). Tenant isolation depends entirely on the callers: the JSON API route `GET /courses/{id}/search` first calls `_require_owned_course` (returning 404 for non-owned courses) before invoking `retrieve.search`, and the pipeline only links within a course the user already owns. The `store.get_lecture` calls inside `search`/`find_links` are made with the default `owner_id=None` (the internal/system path), so the module itself does no owner check.
- `find_links` returns at most one link per topic (the first qualifying hit, after which it breaks), and it silently relies on the vector store returning hits in increasing-distance order; there is no explicit re-sorting in this module to guarantee the "most similar" hit is evaluated first.
- The Stretch linking path in the pipeline is wrapped in a bare `try/except: pass`, so any retrieval or persistence error during link-finding is swallowed and the lecture is simply stored without builds-on links.
- `search` does not surface a similarity/distance score to its callers (only `find_links` computes and returns `similarity`), so API search results carry source and location metadata but no relevance score.
