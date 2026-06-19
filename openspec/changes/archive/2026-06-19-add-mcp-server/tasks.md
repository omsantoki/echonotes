## 1. Dependency & configuration

- [x] 1.1 Confirm the current FastMCP / `mcp` Python SDK release and its API for (a) building a streamable-HTTP ASGI app and (b) reading per-request headers inside a tool; pin the chosen version in `backend/requirements.txt` (and `requirements-*.txt` as applicable)
- [x] 1.2 Add an `ENABLE_MCP` setting (default `false`) to `backend/app/config.py` Settings, plus optional `MCP_ASK_RATE_LIMIT` / window settings; surface defaults in `.env.example`
- [x] 1.3 Document the new flags in `render.yaml` env block (kept disabled in prod by default)

## 2. Shared auth resolution

- [x] 2.1 Extract the bearer-token → user resolution (`decode_session_token` + `store.get_user`) out of `app.auth.deps.get_current_user` into a reusable helper in `app.auth` (e.g. `resolve_bearer_user(authorization) -> dict | None`)
- [x] 2.2 Refactor `get_current_user` to call the shared helper (behavior unchanged; existing 401 semantics preserved)

## 3. MCP server module

- [x] 3.1 Create `backend/app/mcp_server.py` that builds the streamable-HTTP MCP app and a per-request dependency that reads `Authorization: Bearer …` and resolves the user via the shared helper, refusing as an auth error on missing/invalid/expired/orphaned tokens
- [x] 3.2 Implement `list_courses` (owner-scoped `store.list_courses`) — no tenant parameter in the schema
- [x] 3.3 Implement `search_notes(course_id, q)` — verify ownership server-side (404-style not-found on non-owned/missing), then return `retrieve.search(course_id, q)`
- [x] 3.4 Implement `get_lecture(lecture_id)` and `export_lecture(lecture_id)` — owner-scoped read / exported study document, not-found indistinguishable from non-owned
- [x] 3.5 Implement `ask_course(course_id, q)` — owner-scoped; refuse with a "Q&A not enabled" error when `enable_qa` is off (mirror the JSON 503); otherwise call `answer.answer_question` (reusing the semantic cache) and surface the `cached` flag
- [x] 3.6 Add per-token rate limiting to `ask_course`; refuse with a rate-limit error past the configured limit/window without affecting other tokens

## 4. Mount & wiring

- [x] 4.1 In `backend/app/main.py`, mount the MCP app at `/mcp` only when `ENABLE_MCP` is set; leave the surface entirely absent (no routes) when off
- [x] 4.2 Verify the mount does not interfere with the existing `_lifespan` orphan recovery, CORS, the `/assets` mount, or the JSON `{"error": {...}}` envelope handlers

## 5. Tests (hermetic)

- [x] 5.1 Test the shared auth helper and that `get_current_user` still returns 401 on the same cases as before (no regression)
- [x] 5.2 Test MCP auth: missing/malformed/invalid/expired/orphaned bearer → auth refusal, tool body never runs (mock external I/O, force local backends)
- [x] 5.3 Test tenant safety: tool input schemas expose no `owner_id`/`user_id`; a cross-tenant `course_id`/`lecture_id` returns the same not-found as a non-existent id (no field leak, no 403-style distinction)
- [x] 5.4 Test the tool catalog is read-only (no create/upload/edit/delete tool present) and returns owner-scoped results matching the underlying functions
- [x] 5.5 Test `ask_course`: refuses without an LLM call when `enable_qa` is off; cache hit returns `cached`; per-token rate limit throttles only the offending token
- [x] 5.6 Test the `ENABLE_MCP` flag: off → `/mcp` not mounted and app behavior unchanged; on → MCP reachable

## 6. Validation & housekeeping

- [x] 6.1 Validated transport+auth+owner-scoping end-to-end over real HTTP. Committed `scripts/validate_mcp.py` (runs anywhere, no ML stack — PASS: 5 tools, owner-scoped list, search, ready lecture, cross-tenant/missing → not-found, no-bearer → refused). Also wired the same MCP checks into `scripts/validate_demo.py` so the project's demo gate exercises the tools against the REAL pipeline-merged demo lecture (`backend/samples/`); that full run needs the local stack/Ollama, run by the user with `python scripts/validate_demo.py`
- [x] 6.2 Document MCP client setup (mount URL, bearer-token header) in the README / relevant docs
- [x] 6.3 Run `graphify update .` to refresh the code-structure graph after the new module/mount
