"""FastAPI auth dependency (feature 002, FR-19/FR-22).

`get_current_user` decodes the `Authorization: Bearer <jwt>` session token into the
owning user (a registry dict). A missing / malformed / invalid / expired token — or
a token for a user that no longer exists — yields **401** `unauthorized`. Data routes
depend on this and pass `user["id"]` to `store` as the `owner_id`, so the owner filter
is applied in the storage layer (Art. X).

The bearer → user resolution lives in `resolve_bearer_user`, shared verbatim by the MCP
server (capability: mcp-server) so the two authenticated surfaces can never drift.
"""

from __future__ import annotations

from fastapi import Header, HTTPException

from app import store
from app.auth import security


def _unauthorized() -> HTTPException:
    return HTTPException(401, detail={"code": "unauthorized",
                                      "message": "Authentication required."})


def _bearer_token(authorization: str | None) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


def resolve_bearer_user(authorization: str | None) -> dict | None:
    """Resolve an `Authorization: Bearer <jwt>` header value to the owning user, or None.

    Returns None on EVERY failure mode — missing/malformed header, invalid/expired/
    non-session token, or a token whose user no longer exists — so callers decide how to
    surface it (the JSON API raises 401; the MCP server raises a tool auth error). No data
    is read unless a valid session resolves to an existing user.
    """
    token = _bearer_token(authorization)
    if not token:
        return None
    user_id = security.decode_session_token(token)
    if not user_id:
        return None
    return store.get_user(user_id)


def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    user = resolve_bearer_user(authorization)
    if user is None:
        raise _unauthorized()
    return user
