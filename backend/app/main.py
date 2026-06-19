"""EchoNotes FastAPI app.

Phase 0 shipped the health route; Phase 1 (Core) wires the course/lecture
pipeline, the server-rendered UI, the preserved-diagram mount, and the contract's
`{"error": {...}}` envelope.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import store, web
from app.api import courses, lectures
from app.auth import router as auth_router
from app.config import active_async, active_storage, get_settings
from app.models import LectureStatus

log = logging.getLogger("echonotes")


def _recover_orphaned_lectures() -> None:
    # Recover orphaned lectures ONLY in inline mode. When the pipeline runs in-process
    # (task_always_eager / no broker), a web restart truly kills in-flight work, so we
    # mark it failed instead of leaving an endless "processing" spinner. With a Celery
    # broker the worker survives web restarts and a deploy must NOT touch lectures the
    # worker is still processing — durability there comes from acks_late + retries.
    if active_async()["tasks"] == "inline":
        try:
            # System path: scan ALL lectures (every owner) — recovery is not per-user.
            for lec in store.list_all_lectures():
                if lec.get("status") in ("processing", "uploaded"):
                    store.update_lecture(
                        lec["id"], status=LectureStatus.failed,
                        progress="Processing was interrupted (the server restarted). Please re-upload.",
                    )
        except Exception:
            pass


# Build the MCP server (capability: mcp-server) ONLY when ENABLE_MCP is set — when off,
# fastmcp is never imported and no /mcp routes exist (the surface is entirely absent).
# Fail closed: if the flag is on but init fails, log loudly and run without MCP rather
# than refusing to boot the whole API.
_mcp_app = None
if get_settings().enable_mcp:
    try:
        from app.mcp_server import build_mcp_app
        _mcp_app = build_mcp_app()
    except Exception:
        log.exception("ENABLE_MCP is set but the MCP server failed to initialize; "
                      "continuing without it.")
        _mcp_app = None


@asynccontextmanager
async def _lifespan(app: FastAPI):
    # The MCP streamable-HTTP transport has its own lifespan (session manager); nest it
    # so it starts/stops with the app. When MCP is off, just do the orphan recovery.
    if _mcp_app is not None:
        async with _mcp_app.lifespan(app):
            _recover_orphaned_lectures()
            yield
    else:
        _recover_orphaned_lectures()
        yield


app = FastAPI(title="EchoNotes", version="0.1.0", lifespan=_lifespan)

# Allow the separate React frontend (different origin in prod) to call the API
# and load /assets cross-origin. Dev uses the Vite proxy, so this is a no-op there.
_origins = [o.strip() for o in get_settings().cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve preserved diagram images. No audio is ever stored here (Art. IV).
_assets = Path(get_settings().data_dir) / "assets"
_assets.mkdir(parents=True, exist_ok=True)
app.mount("/assets", StaticFiles(directory=str(_assets)), name="assets")

app.include_router(auth_router)
app.include_router(courses.router)
app.include_router(lectures.router)
# The server-rendered console is single-tenant (acts as the bootstrap admin with no
# login), so it is mounted ONLY when explicitly enabled — on by default for local dev,
# off in production (render.yaml) so the public backend exposes no unauthenticated
# course-create / lecture-upload surface. See Settings.enable_web_console.
if get_settings().enable_web_console:
    app.include_router(web.router)
else:
    log.info("Server-rendered web console disabled (ENABLE_WEB_CONSOLE=false).")

# Mount the MCP server at /mcp when enabled (read-only, owner-scoped tools; see
# app/mcp_server.py). Off by default, so the public surface adds nothing unless asked.
if _mcp_app is not None:
    app.mount("/mcp", _mcp_app)
    log.info("MCP server mounted at /mcp (ENABLE_MCP=true).")


@app.get("/api/health")
def health() -> dict:
    """Liveness + config sanity (reveals whether a key is set, never the key)."""
    s = get_settings()
    if s.provider == "local":
        models = {"transcribe": s.whisper_model, "embed": s.local_embedding_model,
                  "merge": f"ollama:{s.ollama_model}"}
    else:
        models = {"transcribe": s.transcribe_model, "embed": s.embedding_model,
                  "merge": s.chat_model, "openai_key_set": bool(s.openai_api_key)}
    return {"status": "ok", "provider": s.provider, "models": models,
            "storage": active_storage(), "async": active_async()}


_STATUS_CODE = {400: "bad_request", 401: "unauthorized", 403: "forbidden",
                404: "not_found", 409: "conflict", 413: "payload_too_large",
                503: "service_unavailable"}


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Shape every error as contracts/api.md mandates: {"error": {code, message}}.

    Registered on the Starlette base class so both our explicit raises and
    framework routing errors (e.g. unknown-route 404s) get the envelope.
    """
    detail = exc.detail
    if isinstance(detail, dict) and "code" in detail and "message" in detail:
        err = detail
    else:
        err = {"code": _STATUS_CODE.get(exc.status_code, "error"), "message": str(detail)}
    return JSONResponse(status_code=exc.status_code, content={"error": err})


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    """Malformed requests (missing form fields, bad types) also use the envelope."""
    first = exc.errors()[0] if exc.errors() else {}
    loc = ".".join(str(p) for p in first.get("loc", []))
    msg = f"{loc}: {first.get('msg', 'invalid request')}".strip(": ")
    return JSONResponse(status_code=422,
                        content={"error": {"code": "validation_error", "message": msg}})


@app.exception_handler(Exception)
async def unhandled_handler(request: Request, exc: Exception):
    # Log the real error server-side; return a generic message so internal details
    # (DB/driver/stack text, secrets in connection strings) never leak to clients.
    log.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500,
                        content={"error": {"code": "internal_error",
                                           "message": "An unexpected error occurred."}})
