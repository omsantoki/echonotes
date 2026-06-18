"""Auth business logic (feature 002): signup → OTP → set-password → login, Google
sign-in, and forgot/reset. Talks to `store` (users + hashed tokens), `email`, and
`auth.security` / `auth.google`.

Two cross-cutting rules from Constitution Art. X are enforced here:
  * No account-existence leak — signup and forgot-password always return the same
    neutral message; login returns one generic error for unknown-email and wrong-
    password alike.
  * No plaintext secrets — only hashes reach `store`; OTPs / links are emailed (or
    logged in dev) exactly once.
"""

from __future__ import annotations

import re

from fastapi import HTTPException

from app import email as email_mod
from app import store
from app.auth import google as google_mod
from app.auth import security
from app.config import get_settings
from app.models import AuthProvider, AuthToken, TokenKind, User

PASSWORD_MIN = 8
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

_NEUTRAL_SIGNUP = "If that email can sign up, a verification code is on its way."
_NEUTRAL_FORGOT = "If that account exists, a password reset link is on its way."


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def _require_valid_email(email: str) -> str:
    email = _normalize_email(email)
    if not _EMAIL_RE.match(email):
        raise HTTPException(400, detail={"code": "invalid_email",
                                         "message": "Enter a valid email address."})
    return email


def _require_strong_password(password: str) -> None:
    if not password or len(password) < PASSWORD_MIN:
        raise HTTPException(400, detail={"code": "weak_password",
            "message": f"Password must be at least {PASSWORD_MIN} characters."})


def ensure_bootstrap_admin() -> dict:
    """Return the bootstrap admin user (BOOTSTRAP_ADMIN_EMAIL), creating it if missing.

    Used by the legacy-course migration and by the single-tenant server-rendered console
    (web.py) so that console is always bound to a concrete owner — never the unscoped
    "all courses" path (which would cross tenants). The admin starts password-less and
    verified; claim it with forgot-password to set a password (FR-25, data-model.md).
    """
    email = _normalize_email(get_settings().bootstrap_admin_email)
    user = store.get_user_by_email(email)
    if user:
        return user
    created = store.create_user(User(email=email, auth_provider=AuthProvider.local,
                                     email_verified=True))
    return store.get_user(created.id)


def _public_user(user: dict) -> dict:
    """The user shape safe to return — never a password hash or token (Art. X)."""
    return {
        "id": user["id"],
        "email": user["email"],
        "auth_provider": user.get("auth_provider", "local"),
        "email_verified": bool(user.get("email_verified")),
        "created_at": user.get("created_at"),
    }


def _token_is_live(tok: dict | None) -> bool:
    return bool(tok) and not tok.get("used") and not security.is_expired(tok["expires_at"])


def _issue_token(user_id: str, kind: TokenKind, ttl: int) -> str:
    """Mint a secret, store ONLY its hash (invalidating older ones of this kind), return the plaintext."""
    store.invalidate_auth_tokens(user_id, kind)  # one active token per kind — no replay
    secret = security.generate_otp() if kind is TokenKind.otp else security.generate_token()
    store.create_auth_token(AuthToken(
        user_id=user_id, kind=kind, token_hash=security.hash_secret(secret),
        expires_at=security.expires_in(ttl),
    ))
    return secret


def _session_response(user: dict) -> dict:
    return {"session_token": security.create_session_token(user["id"]),
            "user": _public_user(user)}


# --------------------------------------------------------------------------- #
# Signup → OTP → set-password
# --------------------------------------------------------------------------- #

def signup(email: str) -> dict:
    """Create an unverified account (if new) and email a 6-digit OTP. Never reveals
    whether the email already existed (FR-14)."""
    email = _require_valid_email(email)
    user = store.get_user_by_email(email)

    # An already-usable login (verified local account with a password) is left alone —
    # don't re-issue codes or hint that it exists; the user should log in / reset instead.
    if user and user.get("email_verified") and user.get("password_hash"):
        return {"ok": True, "message": _NEUTRAL_SIGNUP}

    if user is None:
        created = store.create_user(User(email=email, auth_provider=AuthProvider.local))
        user = store.get_user(created.id)

    otp = _issue_token(user["id"], TokenKind.otp, get_settings().otp_ttl)
    email_mod.send_otp_email(user["email"], otp)
    return {"ok": True, "message": _NEUTRAL_SIGNUP}


def verify_otp(email: str, otp: str) -> dict:
    """Verify the OTP; on success mark the email verified and issue a single-use
    set-password token (FR-16)."""
    bad = HTTPException(400, detail={"code": "invalid_otp",
                                     "message": "That code is invalid or has expired."})
    email = _normalize_email(email)
    user = store.get_user_by_email(email)
    if not user:
        raise bad
    tok = store.find_auth_token(TokenKind.otp, user_id=user["id"])
    if not _token_is_live(tok):
        raise bad
    if tok["attempts"] >= get_settings().otp_max_attempts:
        store.bump_auth_token(tok["id"], used=True)  # lock it out
        raise bad
    if security.hash_secret(otp or "") != tok["token_hash"]:
        store.bump_auth_token(tok["id"], attempts=tok["attempts"] + 1)
        raise bad

    store.bump_auth_token(tok["id"], used=True)
    if not user.get("email_verified"):
        store.update_user(user["id"], {"email_verified": True})
    set_password_token = _issue_token(user["id"], TokenKind.set_password,
                                      get_settings().reset_token_ttl)
    return {"set_password_token": set_password_token}


def set_password(token: str, password: str) -> dict:
    """Set the initial password using the verify-otp token, and log the user in (FR-17)."""
    _require_strong_password(password)
    tok = store.find_auth_token(TokenKind.set_password, token_hash=security.hash_secret(token or ""))
    if not _token_is_live(tok):
        raise HTTPException(400, detail={"code": "invalid_token",
            "message": "This link is invalid or has expired. Start sign-up again."})
    user = store.get_user(tok["user_id"])
    if not user:
        raise HTTPException(400, detail={"code": "invalid_token", "message": "Account not found."})
    store.update_user(user["id"], {"password_hash": security.hash_password(password),
                                   "email_verified": True})
    store.bump_auth_token(tok["id"], used=True)
    return _session_response(store.get_user(user["id"]))


# --------------------------------------------------------------------------- #
# Login
# --------------------------------------------------------------------------- #

def login(email: str, password: str) -> dict:
    """Email + password → session token; rejects unverified accounts; no enumeration (FR-18)."""
    invalid = HTTPException(401, detail={"code": "invalid_credentials",
                                         "message": "Invalid email or password."})
    email = _normalize_email(email)
    user = store.get_user_by_email(email)
    if not user or not security.verify_password(password, user.get("password_hash")):
        raise invalid  # same response for unknown email and wrong password
    if not user.get("email_verified"):
        raise HTTPException(403, detail={"code": "email_not_verified",
            "message": "Please verify your email before logging in."})
    return _session_response(user)


# --------------------------------------------------------------------------- #
# Google sign-in (Strong)
# --------------------------------------------------------------------------- #

def google_auth(id_token: str) -> dict:
    """Verify a Google ID token server-side, then find-or-create a verified user (FR-26)."""
    try:
        claims = google_mod.verify_google_id_token(id_token)
    except google_mod.GoogleNotConfigured:
        raise HTTPException(503, detail={"code": "google_not_configured",
            "message": "Google sign-in is not configured on this server."})
    except google_mod.GoogleAuthError as exc:
        raise HTTPException(400, detail={"code": "invalid_google_token",
            "message": f"Could not verify the Google sign-in: {exc}"})

    user = store.get_user_by_google_sub(claims["sub"])
    if not user:
        existing = store.get_user_by_email(claims["email"])
        if existing:
            # Link Google to an existing local account (same email) and trust the verified email.
            store.update_user(existing["id"], {"google_sub": claims["sub"], "email_verified": True})
            user = store.get_user(existing["id"])
        else:
            created = store.create_user(User(
                email=claims["email"], auth_provider=AuthProvider.google,
                google_sub=claims["sub"], email_verified=True,
            ))
            user = store.get_user(created.id)
    return _session_response(user)


# --------------------------------------------------------------------------- #
# Forgot / reset password (Strong)
# --------------------------------------------------------------------------- #

def forgot_password(email: str) -> dict:
    """Email a reset link if the account exists; always return the same neutral message (FR-27)."""
    email = _normalize_email(email)
    user = store.get_user_by_email(email)
    if user:
        secret = _issue_token(user["id"], TokenKind.reset, get_settings().reset_token_ttl)
        reset_url = f"{get_settings().frontend_url.rstrip('/')}/reset-password?token={secret}"
        email_mod.send_reset_email(user["email"], reset_url)
    return {"ok": True, "message": _NEUTRAL_FORGOT}


def reset_password(token: str, password: str) -> dict:
    """Set a new password using a reset token, then consume the token (FR-28)."""
    _require_strong_password(password)
    tok = store.find_auth_token(TokenKind.reset, token_hash=security.hash_secret(token or ""))
    if not _token_is_live(tok):
        raise HTTPException(400, detail={"code": "invalid_token",
            "message": "This reset link is invalid or has expired. Request a new one."})
    user = store.get_user(tok["user_id"])
    if not user:
        raise HTTPException(400, detail={"code": "invalid_token", "message": "Account not found."})
    store.update_user(user["id"], {"password_hash": security.hash_password(password),
                                   "email_verified": True})
    store.bump_auth_token(tok["id"], used=True)
    return {"ok": True}
