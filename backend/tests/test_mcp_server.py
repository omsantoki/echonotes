"""MCP server tests (capability: mcp-server).

Hermetic: the conftest forces local backends and we never start the streamable-HTTP
transport or call an LLM. The tools are thin adapters over plain core functions
(`_list_courses`, `_search_notes`, …) that take a resolved `user` dict, so the owner
scoping, Q&A gating, and rate limiting are exercised directly. Schemas are inspected via
the in-memory FastMCP client; the ENABLE_MCP mount is checked in an isolated subprocess.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys

import pytest

from app import mcp_server as m
from app.auth import security
from app.auth.deps import get_current_user, resolve_bearer_user
from app.config import get_settings
from tests.conftest import auth_headers  # noqa: F401  (kept for parity with other suites)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend/


def _user(register, email):
    """Register a user and return their real registry dict (via the shared resolver)."""
    tok = register(email)["session_token"]
    user = resolve_bearer_user(f"Bearer {tok}")
    assert user is not None
    return user, tok


def _make_course(client, token, name):
    r = client.post("/api/courses", json={"name": name}, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _seed_ready_lecture(course_id, title="Owned lecture"):
    from app import store
    from app.models import Lecture, LectureStatus

    lec = Lecture(course_id=course_id, title=title, status=LectureStatus.ready, progress="Ready.")
    store.create_lecture(lec)
    return lec.id


# --------------------------------------------------------------------------- #
# Shared bearer→user resolution (the single auth path for HTTP and MCP)
# --------------------------------------------------------------------------- #

def test_resolve_bearer_user_rejects_bad_tokens(client, register):
    assert resolve_bearer_user(None) is None
    assert resolve_bearer_user("") is None
    assert resolve_bearer_user("Bearer ") is None
    assert resolve_bearer_user("Token abc") is None          # not a bearer scheme
    assert resolve_bearer_user("Bearer not.a.jwt") is None   # decode failure
    # A well-signed session token for a user that does not exist (orphaned) → None.
    assert resolve_bearer_user(f"Bearer {security.create_session_token('ghost-id')}") is None


def test_resolve_bearer_user_accepts_valid_session(client, register):
    user, tok = _user(register, "a@example.com")
    assert resolve_bearer_user(f"Bearer {tok}")["id"] == user["id"]


def test_get_current_user_still_401s_on_same_cases(client, register):
    # Regression: the HTTP dependency keeps its 401 behavior after the refactor.
    from fastapi import HTTPException

    for bad in (None, "Bearer ", "Bearer not.a.jwt", "Token abc"):
        with pytest.raises(HTTPException) as ei:
            get_current_user(bad)
        assert ei.value.status_code == 401
    _, tok = _user(register, "ok@example.com")
    assert get_current_user(f"Bearer {tok}")["id"] == resolve_bearer_user(f"Bearer {tok}")["id"]


# --------------------------------------------------------------------------- #
# _current_user(): reads the bearer header off the active request
# --------------------------------------------------------------------------- #

def test_current_user_resolves_request_header(client, register, monkeypatch):
    user, tok = _user(register, "a@example.com")
    monkeypatch.setattr(m, "get_http_headers", lambda include=None: {"authorization": f"Bearer {tok}"})
    assert m._current_user()["id"] == user["id"]


def test_current_user_refuses_without_bearer(client, monkeypatch):
    monkeypatch.setattr(m, "get_http_headers", lambda include=None: {})
    with pytest.raises(m.ToolError):
        m._current_user()


# --------------------------------------------------------------------------- #
# Tool catalog: read-only, and NO tool exposes a tenant parameter
# --------------------------------------------------------------------------- #

def _list_client_tools():
    from fastmcp import Client

    async def _run():
        async with Client(m.mcp) as c:
            return await c.list_tools()

    return asyncio.run(_run())


def test_tool_schemas_expose_no_tenant_parameter(client):
    for t in _list_client_tools():
        props = set((t.inputSchema or {}).get("properties", {}))
        assert not (props & {"owner_id", "user_id", "owner", "tenant"}), f"{t.name} leaks a tenant param"


def test_catalog_is_the_expected_read_only_set(client):
    names = {t.name for t in _list_client_tools()}
    assert names == {"list_courses", "search_notes", "ask_course", "get_lecture", "export_lecture"}
    # No create/upload/edit/delete tool is offered (v1 is read-only).
    assert not any(v in n for n in names for v in ("create", "upload", "delete", "edit", "update"))


# --------------------------------------------------------------------------- #
# Owner scoping: not-owned == not-found (existence never leaked)
# --------------------------------------------------------------------------- #

def test_list_courses_is_owner_scoped(client, register, monkeypatch):
    monkeypatch.setattr("app.retrieve.search", lambda course_id, q, n=None: [])
    user_a, tok_a = _user(register, "a@example.com")
    user_b, _ = _user(register, "b@example.com")
    a_course = _make_course(client, tok_a, "A — Thermo")

    assert [c["id"] for c in m._list_courses(user_a)] == [a_course]
    assert m._list_courses(user_b) == []


def test_search_notes_cross_tenant_is_not_found(client, register, monkeypatch):
    monkeypatch.setattr("app.retrieve.search", lambda course_id, q, n=None: [])
    user_a, tok_a = _user(register, "a@example.com")
    user_b, _ = _user(register, "b@example.com")
    a_course = _make_course(client, tok_a, "A — Private")

    # Owner gets results; the shape mirrors the JSON /search route.
    assert m._search_notes(user_a, a_course, "entropy") == {"query": "entropy", "results": []}
    # A different owner — and a truly-missing id — both raise the SAME not-found.
    with pytest.raises(m.ToolError) as foreign:
        m._search_notes(user_b, a_course, "entropy")
    with pytest.raises(m.ToolError) as missing:
        m._search_notes(user_b, "does-not-exist", "entropy")
    assert str(foreign.value) == f"No course {a_course}."
    assert "does-not-exist" in str(missing.value)


def test_get_and_export_lecture_cross_tenant_is_not_found(client, register):
    user_a, tok_a = _user(register, "a@example.com")
    user_b, _ = _user(register, "b@example.com")
    a_course = _make_course(client, tok_a, "A — With lecture")
    lec_id = _seed_ready_lecture(a_course)

    assert m._get_lecture(user_a, lec_id)["status"] == "ready"
    with pytest.raises(m.ToolError):
        m._get_lecture(user_b, lec_id)
    with pytest.raises(m.ToolError):
        m._export_lecture(user_b, lec_id, "md")


# --------------------------------------------------------------------------- #
# ask_course: honors ENABLE_QA, uses the cache flag, rate-limited per token
# --------------------------------------------------------------------------- #

def test_ask_course_refuses_when_qa_disabled(client, register, monkeypatch):
    calls = {"n": 0}
    monkeypatch.setattr("app.answer.answer_question", lambda c, q: calls.__setitem__("n", calls["n"] + 1) or {})
    monkeypatch.setenv("ENABLE_QA", "false")
    get_settings.cache_clear()
    user_a, tok_a = _user(register, "a@example.com")
    a_course = _make_course(client, tok_a, "A — Quiet")

    with pytest.raises(m.ToolError):
        m._ask_course(user_a, a_course, "what is entropy?")
    assert calls["n"] == 0  # never reached the LLM


def test_ask_course_returns_cached_flag(client, register, monkeypatch):
    monkeypatch.setattr("app.answer.answer_question",
                        lambda c, q: {"answer": "Entropy is disorder.", "sources": [], "cached": True})
    monkeypatch.setenv("ENABLE_QA", "true")
    get_settings.cache_clear()
    m._reset_rate_limits()
    user_a, tok_a = _user(register, "a@example.com")
    a_course = _make_course(client, tok_a, "A — Asking")

    out = m._ask_course(user_a, a_course, "what is entropy?")
    assert out["cached"] is True and out["query"] == "what is entropy?"


def test_ask_course_rate_limited_per_token_in_process(client, register, monkeypatch):
    # No Redis (conftest forces REDIS_URL="") → the in-process fallback window is exercised.
    monkeypatch.setattr("app.answer.answer_question", lambda c, q: {"answer": "ok", "sources": [], "cached": False})
    monkeypatch.setenv("ENABLE_QA", "true")
    monkeypatch.setenv("MCP_ASK_RATE_LIMIT", "2")
    monkeypatch.setenv("MCP_ASK_RATE_WINDOW", "60")
    get_settings.cache_clear()
    m._reset_rate_limits()
    user_a, tok_a = _user(register, "a@example.com")
    user_b, tok_b = _user(register, "b@example.com")
    a_course = _make_course(client, tok_a, "A — Busy")
    b_course = _make_course(client, tok_b, "B — Calm")

    # A burns its 2-call budget, the 3rd is throttled…
    m._ask_course(user_a, a_course, "q1")
    m._ask_course(user_a, a_course, "q2")
    with pytest.raises(m.ToolError):
        m._ask_course(user_a, a_course, "q3")
    # …while B (a different token) is unaffected.
    assert m._ask_course(user_b, b_course, "q1")["answer"] == "ok"


def test_ask_course_rate_limited_via_shared_redis(client, register, monkeypatch):
    # With Redis configured the limit is enforced by a shared counter (multi-worker safe).
    import fakeredis

    from app import cache

    fake = fakeredis.FakeStrictRedis(decode_responses=True)
    monkeypatch.setattr(cache, "_redis", lambda: fake)
    monkeypatch.setattr("app.answer.answer_question", lambda c, q: {"answer": "ok", "sources": [], "cached": False})
    monkeypatch.setenv("ENABLE_QA", "true")
    monkeypatch.setenv("MCP_ASK_RATE_LIMIT", "2")
    monkeypatch.setenv("MCP_ASK_RATE_WINDOW", "60")
    get_settings.cache_clear()
    m._reset_rate_limits()  # ensure ONLY the redis counter is in play
    user_a, tok_a = _user(register, "a@example.com")
    a_course = _make_course(client, tok_a, "A — Busy")

    m._ask_course(user_a, a_course, "q1")
    m._ask_course(user_a, a_course, "q2")
    with pytest.raises(m.ToolError):
        m._ask_course(user_a, a_course, "q3")
    # The throttle lives in Redis, not process memory.
    assert any(k.startswith(f"mcp:ask:{user_a['id']}:") for k in fake.keys("*"))


# --------------------------------------------------------------------------- #
# ENABLE_MCP flag: mounted only when on (checked in an isolated subprocess so the
# import-time mount decision is genuinely re-evaluated and never pollutes other tests)
# --------------------------------------------------------------------------- #

def _mcp_mounted(enable_mcp: str) -> bool:
    env = {**os.environ, "ENABLE_MCP": enable_mcp,
           "DATABASE_URL": "", "QDRANT_URL": "", "CHROMA_HTTP_URL": "", "S3_BUCKET": "",
           "PROVIDER": "local", "JWT_SECRET": "test-secret", "DATA_DIR": os.environ.get("DATA_DIR", "/tmp")}
    code = "import app.main as m; print(any(getattr(r,'path','')=='/mcp' for r in m.app.routes))"
    out = subprocess.run([sys.executable, "-c", code], env=env, cwd=ROOT,
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    return out.stdout.strip() == "True"


def test_mcp_absent_when_flag_off():
    assert _mcp_mounted("false") is False


def test_mcp_mounted_when_flag_on():
    assert _mcp_mounted("true") is True
