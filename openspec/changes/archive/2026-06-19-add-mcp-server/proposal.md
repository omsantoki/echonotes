## Why

EchoNotes already turns lectures into source-labeled, course-organized study notes and exposes cross-lecture semantic search and grounded RAG Q&A over the JSON API. But that knowledge is only reachable through the EchoNotes web UI. Students increasingly work inside AI clients (Claude Code, Claude Desktop, editors) and want to ask *"what did my course say about X?"* without leaving that context. The Model Context Protocol (MCP) is the emerging standard for exposing an application's data and actions to those clients. Adding a hosted MCP server lets EchoNotes' existing read capabilities become first-class tools in any MCP client — with the same per-user isolation guarantees the JSON API already enforces.

## What Changes

- **New `/mcp` endpoint** mounted on the existing FastAPI app: a streamable-HTTP MCP server (Python `mcp` SDK / FastMCP). One Render service, no new infrastructure — it rides the existing `render.yaml`.
- **Read-only MCP tools**, each a thin wrapper over code that already exists and each strictly owner-scoped:
  - `list_courses` → `store.list_courses`
  - `search_notes(course_id, q)` → `retrieve.search`
  - `ask_course(course_id, q)` → `answer.answer_question` (honors the Q&A feature flag + semantic cache)
  - `get_lecture(lecture_id)` / `export_lecture(lecture_id)` → lecture read/export logic
- **Bearer-token auth (v1):** the MCP request carries `Authorization: Bearer <session JWT>`, resolved by the same `decode_session_token` + `store.get_user` path the JSON API uses. The token is pasted into the client's MCP config (works with Claude Code today).
- **Tenant-safety guarantee:** MCP tools NEVER accept `owner_id`/`user_id` as a parameter — identity comes only from the validated token, and `owner_id` is derived server-side, so a non-owned or missing resource is indistinguishable (same as the JSON API; existence is never leaked).
- **Feature-flagged + rate-limited:** the MCP surface is gated by a config flag (off by default in prod until enabled); `ask_course` is per-token rate-limited because it incurs LLM cost.
- **Out of scope (v2 follow-on):** OAuth 2.1 remote-server authorization for a polished Claude Desktop connector UX, and any write/mutating tools (upload, delete). Noted, not built here.

## Capabilities

### New Capabilities
- `mcp-server`: A hosted MCP server surface that exposes EchoNotes' read capabilities (course listing, cross-lecture search, RAG Q&A, lecture read/export) as owner-scoped MCP tools over streamable HTTP, authenticated by the existing session bearer token and gated by a feature flag.

### Modified Capabilities
<!-- None. The MCP surface REUSES the existing accounts-auth (decode_session_token, get_user) and
     tenant-isolation (owner-scoped storage reads) mechanisms without changing their requirements:
     those specs scope to the JSON course/lecture routes and remain accurate. mcp-server carries its
     own auth + owner-scoping requirements that delegate to the same mechanism. -->

## Impact

- **New code:** `backend/app/mcp_server.py` (tool definitions + bearer resolution); a mount in `backend/app/main.py` at `/mcp`; a new dependency (`mcp` / FastMCP) in `backend/requirements*.txt`; a feature flag + optional rate-limit settings in `backend/app/config.py`.
- **Reused, unchanged:** `app.auth.security.decode_session_token`, `store.get_user`, `store.list_courses`, `retrieve.search`, `answer.answer_question`, and the lecture read/export logic. Owner scoping mirrors `_require_owned_course` (404, not 403).
- **Deploy:** no new service — the MCP app mounts on the running backend; `render.yaml` unchanged except for the new env flag. CORS/error-envelope behavior is preserved for the JSON API.
- **Security surface:** a new authenticated entry point reaching user data; its isolation and the no-`owner_id`-parameter rule are the central correctness concerns. LLM cost exposure via `ask_course` is bounded by the feature flag + per-token rate limit.
- **Tests:** hermetic per project agreements — force local backends, mock external I/O; cover auth rejection, cross-tenant denial, the no-`owner_id`-param contract, flag-off behavior, and rate limiting.
