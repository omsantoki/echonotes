"""Hosted MCP server (capability: mcp-server).

Exposes EchoNotes' READ capabilities as owner-scoped Model Context Protocol tools over
streamable HTTP, mounted on the FastAPI app at `/mcp` — but ONLY when `ENABLE_MCP` is set
(the mount lives in `app/main.py`; when the flag is off, nothing here is imported).

Three invariants make this safe to expose user data on a new authenticated surface:

1. **Same auth as the JSON API.** Each request carries `Authorization: Bearer <session
   JWT>`, resolved by the SHARED `auth.deps.resolve_bearer_user` helper — the exact path
   `get_current_user` uses — so the two surfaces can never drift. A missing/invalid/
   expired/orphaned token raises a tool auth error and the tool body never runs.
2. **Identity comes ONLY from the token.** No tool accepts `owner_id`/`user_id`; the
   owner is derived server-side and pushed into `store`, mirroring `_require_owned_course`.
   A non-owned id returns the SAME not-found as a missing id — existence is never leaked.
3. **Read-only.** No tool creates, mutates, or deletes anything (v1).

Tools are `async` so they run in the request's event-loop context where the HTTP request
is available (FastMCP strips `authorization` from `get_http_headers` by default, so we
opt it back in explicitly). The blocking core calls (embeddings, vector search, the LLM)
are offloaded to a worker thread so they don't stall the event loop.
"""

from __future__ import annotations

import time

import anyio
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_http_headers

from app import answer, cache, retrieve, store
from app.auth.deps import resolve_bearer_user
from app.config import get_settings
from app.render import document_to_html, document_to_markdown

mcp = FastMCP("EchoNotes")


# --------------------------------------------------------------------------- #
# Auth + ownership — derived from the token only, never from a tool argument.
# --------------------------------------------------------------------------- #

def _current_user() -> dict:
    """Resolve the bearer token on the active HTTP request to the owning user.

    `get_http_headers` strips `authorization` by default (to avoid forwarding it
    downstream), so we explicitly include it. Raises a tool auth error on any failure;
    the calling tool's data access never runs.
    """
    headers = get_http_headers(include={"authorization"})
    user = resolve_bearer_user(headers.get("authorization"))
    if user is None:
        raise ToolError(
            "Authentication required: send 'Authorization: Bearer <session token>'."
        )
    return user


def _require_course(user: dict, course_id: str) -> dict:
    """The mcp-server analogue of `_require_owned_course`: not-found == not-owned."""
    course = store.get_course(course_id, owner_id=user["id"])
    if not course:
        raise ToolError(f"No course {course_id}.")
    return course


def _require_lecture(user: dict, lecture_id: str) -> dict:
    lec = store.get_lecture(lecture_id, owner_id=user["id"])
    if not lec:
        raise ToolError(f"No lecture {lecture_id}.")
    return lec


# --------------------------------------------------------------------------- #
# Per-token rate limit for the LLM-backed ask_course tool (cost surface).
# --------------------------------------------------------------------------- #

_ask_calls: dict[str, list[float]] = {}


def _check_ask_rate_limit(user_id: str) -> None:
    """Fixed-window throttle keyed by user.

    Uses Redis when one is configured (the same instance the semantic cache + Celery use),
    so the limit holds ACROSS web workers — a fleet can't each grant a separate budget.
    Falls back to an in-process window when there is no Redis (single dyno / local dev), or
    if Redis hiccups (fail-open to availability rather than refusing a paid-but-valid call).
    """
    s = get_settings()
    limit, window = s.mcp_ask_rate_limit, s.mcp_ask_rate_window
    if limit <= 0:
        return

    r = cache._redis()
    if r is not None:
        # Shared atomic fixed-window counter: INCR a per-(user, window-bucket) key.
        bucket = int(time.time() // window)
        key = f"mcp:ask:{user_id}:{bucket}"
        try:
            n = r.incr(key)
            if n == 1:
                r.expire(key, window)
            if n > limit:
                raise ToolError("Rate limit exceeded for ask_course — try again shortly.")
            return
        except ToolError:
            raise
        except Exception:
            pass  # Redis unreachable → fall through to the in-process window.

    now = time.monotonic()
    recent = [t for t in _ask_calls.get(user_id, []) if now - t < window]
    if len(recent) >= limit:
        raise ToolError("Rate limit exceeded for ask_course — try again shortly.")
    recent.append(now)
    _ask_calls[user_id] = recent


def _reset_rate_limits() -> None:
    """Test hook: clear the in-process rate-limit state."""
    _ask_calls.clear()


# --------------------------------------------------------------------------- #
# Core logic — owner-scoped, free of MCP/HTTP types so it is unit-testable by
# passing a resolved `user` dict directly. The @mcp.tool adapters below just
# resolve the user from the request and delegate here.
# --------------------------------------------------------------------------- #

def _list_courses(user: dict) -> list[dict]:
    return [
        {"id": c["id"], "name": c["name"], "lecture_count": c.get("lecture_count", 0)}
        for c in store.list_courses(owner_id=user["id"])
    ]


def _search_notes(user: dict, course_id: str, query: str) -> dict:
    _require_course(user, course_id)
    return {"query": query, "results": retrieve.search(course_id, query)}


def _ask_course(user: dict, course_id: str, question: str) -> dict:
    _require_course(user, course_id)
    if not get_settings().enable_qa:
        raise ToolError("Q&A is not enabled on this server.")
    _check_ask_rate_limit(user["id"])
    return {"query": question, **answer.answer_question(course_id, question)}


def _get_lecture(user: dict, lecture_id: str) -> dict:
    lec = _require_lecture(user, lecture_id)
    if lec["status"] != "ready":
        return {"id": lec["id"], "status": lec["status"], "progress": lec.get("progress", "")}
    return {"id": lec["id"], "status": "ready", "title": lec["title"],
            "document": store.assemble_document(lecture_id)}


def _export_lecture(user: dict, lecture_id: str, format: str = "md") -> dict:
    lec = _require_lecture(user, lecture_id)
    if lec["status"] != "ready":
        raise ToolError("Lecture is not ready yet.")
    doc = store.assemble_document(lecture_id)
    if format == "html":
        body, content_type = document_to_html(lec["title"], doc, standalone=True), "text/html"
    elif format == "md":
        body, content_type = document_to_markdown(lec["title"], doc), "text/markdown"
    else:
        raise ToolError("format must be 'md' or 'html'.")
    return {"id": lec["id"], "title": lec["title"], "format": format,
            "content_type": content_type, "content": body}


# --------------------------------------------------------------------------- #
# MCP tool adapters (read-only). Blocking core calls run off the event loop.
# --------------------------------------------------------------------------- #

@mcp.tool(name="list_courses")
async def list_courses_tool() -> list[dict]:
    """List the courses you own, with each course's id, name, and lecture count."""
    return _list_courses(_current_user())


@mcp.tool(name="search_notes")
async def search_notes_tool(course_id: str, query: str) -> dict:
    """Semantic search across one course's merged lecture notes. Returns the top matching
    note segments (each with its source lecture, topic, and source type)."""
    user = _current_user()
    return await anyio.to_thread.run_sync(_search_notes, user, course_id, query)


@mcp.tool(name="ask_course")
async def ask_course_tool(course_id: str, question: str) -> dict:
    """Ask a question answered ONLY from one course's notes (grounded RAG). Returns
    {answer, sources, cached}. Requires Q&A to be enabled; rate-limited per user."""
    user = _current_user()
    return await anyio.to_thread.run_sync(_ask_course, user, course_id, question)


@mcp.tool(name="get_lecture")
async def get_lecture_tool(lecture_id: str) -> dict:
    """Fetch one lecture's merged study document, or its processing status if not ready."""
    user = _current_user()
    return await anyio.to_thread.run_sync(_get_lecture, user, lecture_id)


@mcp.tool(name="export_lecture")
async def export_lecture_tool(lecture_id: str, format: str = "md") -> dict:
    """Export a ready lecture's study document as 'md' (markdown) or 'html'."""
    user = _current_user()
    return await anyio.to_thread.run_sync(_export_lecture, user, lecture_id, format)


def build_mcp_app(path: str = "/"):
    """Build the streamable-HTTP ASGI app to mount under /mcp (see app/main.py).

    Mounting at /mcp with an internal path of "/" puts the MCP endpoint at /mcp.
    """
    return mcp.http_app(path=path, transport="http")
