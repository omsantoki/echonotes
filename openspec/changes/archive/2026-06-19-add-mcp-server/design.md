## Context

EchoNotes is a multi-tenant FastAPI backend. Auth is a session JWT resolved by `app.auth.deps.get_current_user` (`Authorization: Bearer <jwt>` → `security.decode_session_token` → `store.get_user`). Every JSON data route passes `user["id"]` to `store` as `owner_id`; the per-owner filter lives in the storage layer, and a non-owned resource returns the same 404 as a missing one (`tenant-isolation`). The two highest-value read capabilities — cross-lecture search (`retrieve.search`) and grounded RAG Q&A (`answer.answer_question`, behind `enable_qa` + a semantic cache) — are already implemented and owner-scoped via `course-management`'s `_require_owned_course`.

This change adds an MCP server surface so MCP clients (Claude Code today; Claude Desktop later) can use those read capabilities as tools. The work is almost entirely *exposure*: the underlying logic exists and must be reused, not reimplemented. The constitution's tenant-isolation rules are the binding constraint — a new authenticated entry point must not become an isolation hole.

## Goals / Non-Goals

**Goals:**
- Expose `list_courses`, `search_notes`, `ask_course`, `get_lecture`, `export_lecture` as owner-scoped, read-only MCP tools.
- Reuse the existing auth (`decode_session_token` + `store.get_user`) and storage owner-scoping verbatim — no parallel auth path.
- Mount on the existing FastAPI app at `/mcp` (one Render service, no new infra).
- Gate behind a config flag (off by default in prod); rate-limit `ask_course`.
- Keep tests hermetic (local backends, mocked external I/O).

**Non-Goals:**
- OAuth 2.1 remote-server authorization (the spec'd path for polished Claude Desktop connectors) — explicit v2 follow-on.
- Any write/mutating tools (upload, create, delete) — read-only in v1.
- Changing the JSON API contract, the web console, or existing capability specs.
- A separate deployable service or new datastore.

## Decisions

### Decision: Mount the MCP server on the existing FastAPI app at `/mcp`
Use the Python MCP SDK / FastMCP, which produces an ASGI sub-application for the streamable-HTTP transport, and `app.mount("/mcp", mcp_app)` in `main.py` alongside `/assets`.
- **Why:** One service, one deploy, one TLS endpoint, one set of secrets — matches the Render single-service model and avoids duplicating config/storage wiring.
- **Alternatives considered:** (a) A separate process/service for MCP — rejected: doubles deploy + secret surface for no isolation benefit since it reads the same store. (b) stdio transport only — rejected: stdio can't be a hosted remote endpoint, which is the chosen v1 direction; we keep streamable HTTP. A local stdio entrypoint can be added later cheaply if wanted.
- **Version caveat:** the exact FastMCP / `mcp` SDK mount API and ASGI integration must be confirmed against the current release at implementation time (training knowledge may be stale) — see Open Questions.

### Decision: Reuse the session JWT as the MCP bearer token (v1)
The MCP request carries `Authorization: Bearer <session JWT>`; a small dependency reads that header, runs `decode_session_token` + `store.get_user`, and yields the user dict — the same three steps as `get_current_user`, factored so both call sites share one implementation.
- **Why:** Zero new credential type, zero new revocation story, and isolation logic is identical to the JSON API. The user pastes their existing token into the client's MCP server config; Claude Code supports per-server `--header "Authorization: Bearer …"`.
- **Alternatives considered:** (a) A new long-lived "MCP API key" type — rejected for v1: adds an issuance/revocation surface; defer until there's demand. (b) OAuth 2.1 — the MCP-spec'd remote auth and the smoothest Claude Desktop UX, but materially more work (authz server, token exchange, consent) — deferred to v2.
- **Refactor note:** extract the bearer→user resolution out of `get_current_user` into a reusable helper in `app.auth` so the MCP path and the HTTP dependency cannot drift.

### Decision: Identity comes only from the token; tools expose no tenant parameter
Tool input schemas contain only domain arguments (`course_id`, `q`, `lecture_id`). `owner_id` is injected server-side from the resolved user and passed to `store`/`_require_owned_course`-equivalent checks. Non-owned ids return the same not-found result as missing ids.
- **Why:** The model (or a malicious prompt) must never be able to name a tenant. This is the single most important correctness property of the change. Mirroring the 404-not-403 rule keeps existence non-leaking.
- **Alternatives considered:** accepting `owner_id` and validating it against the token — rejected: strictly worse (a parameter that must always equal the token is an invitation to a bug or bypass).

### Decision: Feature-flag the surface and rate-limit `ask_course`
Add `ENABLE_MCP` (default off) so the surface is opt-in per deploy; `ask_course` checks `enable_qa` (refusing like the JSON 503 when off) and is throttled per token.
- **Why:** `ask_course` calls the LLM — an unbounded, paid, externally-triggerable surface. The flag bounds rollout; the rate limit bounds cost per caller. The semantic cache already absorbs duplicate questions.
- **Alternatives considered:** global rate limit — rejected: one noisy token would starve others; per-token is fairer and is the natural key since every call is authenticated.

## Risks / Trade-offs

- **Cross-tenant leak via a new entry point** → Reuse the exact `decode_session_token`+`store.get_user`+owner-scoped-store path; no `owner_id` in any tool schema; tests assert cross-tenant calls return not-found and that schemas contain no tenant field.
- **LLM cost abuse through `ask_course`** → `enable_qa` gate + per-token rate limit (a Redis-backed shared fixed-window counter so the limit holds across web workers, with an in-process fallback when no Redis is configured) + the existing semantic cache; default `ENABLE_MCP` off in prod until intentionally enabled.
- **Stale SDK assumptions** → Confirm the current FastMCP/`mcp` mount + header-access API before coding; pin the dependency in `requirements*.txt`. Keep tool bodies thin so an SDK change touches only the adapter layer.
- **Auth logic drift between HTTP and MCP** → Factor the shared bearer→user resolver into one helper; both `get_current_user` and the MCP dependency call it.
- **Streamable-HTTP transport coupling to ASGI lifespan/CORS** → Mount as a sub-app so it inherits the server; verify it does not interfere with the existing `_lifespan` orphan-recovery or the JSON error-envelope handlers (the envelope is JSON-API-specific; MCP has its own error format and that is acceptable).

## Migration Plan

- **Deploy:** additive — new module + a mount guarded by `ENABLE_MCP`. With the flag off (default), behavior is byte-for-byte unchanged, so it ships dark. Enable per environment by setting `ENABLE_MCP=true` (and `ENABLE_QA=true` if `ask_course` is wanted). Update `render.yaml`/`.env.example` to document the flags.
- **Rollback:** set `ENABLE_MCP=false` (or revert the mount) — no schema or data migration is involved, so rollback is config-only.
- **Validation:** exercise the tools against the real demo lecture (`backend/samples/`) through an MCP client before declaring done, per project working agreements.

## Open Questions

- ~~Exact current FastMCP / `mcp` SDK API for mounting + reading per-request headers.~~ **Resolved:** `fastmcp==3.4.2` — `mcp.http_app(transport="http")` for the ASGI app; `get_http_headers(include={"authorization"})` for the header (it strips `authorization` by default, so it must be opted back in). Verified end-to-end over real HTTP.
- ~~Rate-limit storage: in-process vs. shared/Redis.~~ **Resolved:** Redis-backed shared fixed-window counter (reusing `cache._redis()`), with an in-process window as the fallback when no Redis is configured; both paths covered by tests.
- Whether to also ship a thin local stdio entrypoint for single-user dev convenience, or defer entirely to v2 alongside OAuth. **(Still open — deferred.)**
