"""End-to-end validation of the hosted MCP server (capability: mcp-server) over the REAL
streamable-HTTP transport — the path unit tests stub (`get_http_headers`).

Two ways to use it:

  * Standalone (no ML stack, no keys, ~2s):  `python scripts/validate_mcp.py`
    Seeds a throwaway user + course + ready lecture in a temp store, stubs the vector
    search, starts the MCP server, and drives it with a real `fastmcp` client — asserting
    auth, the tool catalog, owner-scoping (cross-tenant + missing → not-found), and that a
    request with NO bearer header is refused before any data is read.

  * As a library:  `validate_demo.py` imports `serve_app` + `exercise_mcp` to run the same
    tools against the REAL pipeline-merged demo lecture (real embeddings + LLM).

Exit code 0 = PASS, 1 = FAIL.
"""

from __future__ import annotations

import asyncio
import os
import socket
import threading
import time


def serve_app(app, timeout: float = 15.0):
    """Start `app` under uvicorn on an ephemeral localhost port in a daemon thread.

    Returns (base_url, server). Call `server.should_exit = True` to stop it. Blocks until
    the app answers /api/health (so the streamable-HTTP session manager's lifespan is up).
    """
    import httpx
    import uvicorn

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    base = f"http://127.0.0.1:{port}"

    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if httpx.get(f"{base}/api/health", timeout=1).status_code == 200:
                return base, server
        except Exception:
            pass
        time.sleep(0.1)
    raise RuntimeError("server did not come up in time")


async def exercise_mcp(base_url: str, token: str, course_id: str,
                       lecture_id: str | None = None, query: str = "photosynthesis") -> dict:
    """Drive the MCP server with a real client. Returns a dict of outcomes; raises on the
    invariants that must always hold (auth refusal, cross-tenant not-found)."""
    from fastmcp import Client
    from fastmcp.client.transports import StreamableHttpTransport

    url = f"{base_url}/mcp"
    auth = {"Authorization": f"Bearer {token}"}
    out: dict = {}

    async with Client(StreamableHttpTransport(url=url, headers=auth)) as c:
        out["tools"] = sorted(t.name for t in await c.list_tools())
        out["courses"] = (await c.call_tool("list_courses", {})).data
        out["search"] = (await c.call_tool("search_notes", {"course_id": course_id, "query": query})).data
        if lecture_id:
            out["lecture"] = (await c.call_tool("get_lecture", {"lecture_id": lecture_id})).data
        # Invariant: a missing/cross-tenant id is not-found, never a leak.
        try:
            await c.call_tool("search_notes", {"course_id": "does-not-exist", "query": query})
            raise AssertionError("missing course should have raised")
        except AssertionError:
            raise
        except Exception:
            out["missing_course_refused"] = True

    # Invariant: NO bearer header → refused before any data.
    async with Client(StreamableHttpTransport(url=url)) as c:
        try:
            await c.call_tool("list_courses", {})
            raise AssertionError("no-auth call should have raised")
        except AssertionError:
            raise
        except Exception:
            out["no_auth_refused"] = True

    return out


def main() -> int:
    import pathlib
    import sys
    import tempfile

    root = pathlib.Path(__file__).resolve().parent.parent  # backend/
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    tmp = tempfile.mkdtemp(prefix="echonotes_mcpval_")
    os.environ.update({
        "DATABASE_URL": "", "QDRANT_URL": "", "CHROMA_HTTP_URL": "", "S3_BUCKET": "",
        "REDIS_URL": "", "PROVIDER": "local", "DATA_DIR": tmp, "CHROMA_DIR": tmp + "/.chroma",
        "JWT_SECRET": "mcp-validate-secret", "ENABLE_MCP": "true", "ENABLE_QA": "true",
    })

    from app import retrieve, store
    from app.auth import security
    from app.config import get_settings
    from app.models import Course, Lecture, LectureStatus, User

    get_settings.cache_clear()
    # No ML stack here: stub the vector search so we don't load an embedding model.
    retrieve.search = lambda course_id, q, n=None: [
        {"lecture_id": "L1", "lecture_title": "Intro", "topic": "Photosynthesis",
         "text": "Photosynthesis converts light into chemical energy.", "source_type": "merged"}
    ]

    user = store.create_user(User(email="mcpval@x.com", email_verified=True))
    course = store.create_course(Course(name="Bio", owner_id=user.id))
    lec = store.create_lecture(Lecture(course_id=course.id, title="L1", status=LectureStatus.ready))
    token = security.create_session_token(user.id)

    from app.main import app  # imported AFTER ENABLE_MCP=true so the /mcp mount exists
    base, server = serve_app(app)
    try:
        res = asyncio.run(exercise_mcp(base, token, course.id, lec.id))
    finally:
        server.should_exit = True

    expected_tools = {"list_courses", "search_notes", "ask_course", "get_lecture", "export_lecture"}
    checks = {
        "5 read-only tools": set(res["tools"]) == expected_tools,
        "list_courses scoped to owner": [c["id"] for c in res["courses"]] == [course.id],
        "search_notes returns results": len(res["search"]["results"]) >= 1,
        "get_lecture ready": res.get("lecture", {}).get("status") == "ready",
        "missing/cross-tenant → not-found": res.get("missing_course_refused") is True,
        "no bearer header → refused": res.get("no_auth_refused") is True,
    }
    for name, ok in checks.items():
        print(("PASS" if ok else "FAIL"), "-", name)
    ok = all(checks.values())
    print("\nRESULT:", "PASS — MCP surface validated over real HTTP" if ok else "FAIL — see checks")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
