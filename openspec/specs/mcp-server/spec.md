# mcp-server Specification

## Purpose
TBD - created by archiving change add-mcp-server. Update Purpose after archive.
## Requirements
### Requirement: MCP server surface mounted on the backend

The system SHALL expose a Model Context Protocol server over streamable HTTP, mounted on the existing FastAPI application at the `/mcp` path, so MCP clients connect to the same backend service that serves the JSON API. The surface SHALL be gated by a configuration flag (e.g. `ENABLE_MCP`) that is off by default, and when disabled the `/mcp` path SHALL NOT be mounted (no MCP routes exist).

#### Scenario: MCP mounted when enabled

- **WHEN** the backend starts with the MCP feature flag enabled
- **THEN** a streamable-HTTP MCP server is reachable under `/mcp` on the same service that serves `/api/...`
- **AND** the JSON API, CORS behavior, and the `{"error": {...}}` envelope are unchanged

#### Scenario: MCP absent when disabled

- **WHEN** the backend starts with the MCP feature flag off (the default)
- **THEN** no MCP routes are mounted and a request to `/mcp` is not served by an MCP handler
- **AND** the rest of the application behaves exactly as before

### Requirement: MCP tool calls require an authenticated session

The system SHALL require a valid `Authorization: Bearer <session JWT>` on MCP requests, resolving it to the owning user via the same `decode_session_token` + `store.get_user` path used by the JSON API's `get_current_user`, before any tool executes against user data. A missing, malformed, invalid, expired, or orphaned token SHALL cause tool execution to be refused as an authentication error, and SHALL NOT read or return any course or lecture data.

#### Scenario: Missing or malformed bearer token is rejected

- **WHEN** an MCP tool is invoked with no `Authorization` header, or one that does not start with `bearer ` (case-insensitive)
- **THEN** the call is refused as an authentication error
- **AND** no course or lecture data is read or returned

#### Scenario: Invalid, expired, or orphaned token is rejected

- **WHEN** the bearer token fails `decode_session_token`, or decodes to a `user_id` for which `store.get_user` returns nothing
- **THEN** the call is refused as an authentication error
- **AND** the tool body never executes

#### Scenario: Valid session resolves to the owning user

- **WHEN** an MCP tool is invoked with a bearer token that decodes to an existing user
- **THEN** the resolved user's `id` is used as the `owner_id` for every storage read the tool performs

### Requirement: MCP tools are owner-scoped and never accept a caller-supplied owner

The system SHALL derive `owner_id` exclusively from the authenticated session token for every MCP tool, and tool input schemas SHALL NOT expose any `owner_id`, `user_id`, or equivalent tenant parameter. A request for a course or lecture the caller does not own SHALL be indistinguishable from a request for one that does not exist (the same not-found result as the JSON API; existence is never leaked, never a "forbidden" that confirms the resource).

#### Scenario: Tool schemas omit any tenant parameter

- **WHEN** an MCP client lists the available tools and inspects their input schemas
- **THEN** no tool accepts `owner_id`, `user_id`, or any parameter that could name or select a tenant
- **AND** the only identity signal honored by the server is the bearer token

#### Scenario: Cross-tenant access yields not-found, not a leak

- **WHEN** an authenticated user invokes a tool with a `course_id` or `lecture_id` owned by a different user
- **THEN** the tool returns the same not-found result it would for an entirely non-existent id
- **AND** no field of the other tenant's resource is revealed, and no error distinguishes "exists but not yours" from "does not exist"

### Requirement: Read-only tool catalog over existing capabilities

The system SHALL expose the following read-only MCP tools, each a thin wrapper over existing backend logic and each owner-scoped per the rules above: `list_courses` (the caller's courses), `search_notes(course_id, q)` (cross-lecture semantic search via `retrieve.search`), `ask_course(course_id, q)` (grounded RAG answer via `answer.answer_question`), `get_lecture(lecture_id)` and `export_lecture(lecture_id)` (lecture read / exported study document). In v1 the system SHALL NOT expose any tool that creates, mutates, or deletes data.

#### Scenario: Listing returns only the caller's courses

- **WHEN** an authenticated user invokes `list_courses`
- **THEN** the result contains exactly the courses owned by that user and no others

#### Scenario: Search returns owner-scoped note segments

- **WHEN** an authenticated user invokes `search_notes` for a course they own with a text query
- **THEN** the tool returns the top matching note segments from that course's lectures, identical to what `retrieve.search` returns for that owner and query

#### Scenario: No mutating tools are offered

- **WHEN** an MCP client lists the available tools
- **THEN** no tool that uploads, creates, edits, or deletes courses, lectures, or notes is present

### Requirement: Q&A tool honors the Q&A flag and is rate-limited

The system SHALL gate the `ask_course` tool on the existing Q&A feature flag (`enable_qa`): when Q&A is disabled the tool SHALL refuse with a clear "Q&A not enabled" error rather than calling the LLM, mirroring the JSON API's 503 behavior. When enabled, `ask_course` SHALL reuse the existing semantic cache and SHALL be rate-limited per authenticated token so a single caller cannot drive unbounded LLM cost.

#### Scenario: Q&A disabled refuses without calling the LLM

- **WHEN** an authenticated user invokes `ask_course` while `enable_qa` is off
- **THEN** the tool returns a "Q&A not enabled" error
- **AND** no LLM request is made

#### Scenario: Repeated questions hit the cache and the rate limit

- **WHEN** an authenticated user invokes `ask_course` with a question semantically equivalent to a recent one
- **THEN** the cached answer is returned without a fresh LLM call (the result indicates it was cached)

#### Scenario: Excessive Q&A from one token is throttled

- **WHEN** a single authenticated token invokes `ask_course` beyond the configured rate limit within the window
- **THEN** further calls from that token are refused with a rate-limit error until the window resets
- **AND** other tokens are unaffected

