"""FastAPI auth dependency (feature 002, FR-19/FR-22).

`get_current_user` decodes the `Authorization: Bearer <jwt>` session token into the
owning user (a registry dict). A missing / malformed / invalid / expired token — or
a token for a user that no longer exists — yields **401** `unauthorized`. Data routes
depend on this and pass `user["id"]` to `store` as the `owner_id`, so the owner filter
is applied in the storage layer (Art. X).
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


def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    token = _bearer_token(authorization)
    if not token:
        raise _unauthorized()
    user_id = security.decode_session_token(token)
    if not user_id:
        raise _unauthorized()
    user = store.get_user(user_id)
    if not user:
        raise _unauthorized()
    return user
