"""Auth primitives (feature 002, Constitution Art. X): password hashing, session
JWTs, OTP / token generation, and at-rest secret hashing.

No plaintext secret is ever stored: passwords are bcrypt-hashed (with a sha256
pre-hash so bcrypt's 72-byte input limit can't silently truncate a long
passphrase), and OTPs / reset tokens are stored only as their sha256 hash. The
session is a stateless HS256 JWT; the signing key comes from env (a clearly-named
dev-only fallback keeps local dev runnable with a blank JWT_SECRET — never ship that).
"""

from __future__ import annotations

import base64
import datetime as dt
import hashlib
import logging
import secrets

import bcrypt
import jwt

from app.config import get_settings

log = logging.getLogger("echonotes.auth")

# Dev-only fallback so local dev runs with a blank JWT_SECRET (Art. VIII/IX). A real
# secret MUST be set in production — see config.Settings.jwt_secret / .env.example.
_DEV_JWT_SECRET = "echonotes-dev-insecure-secret-do-not-use-in-production"


_warned_dev_secret = False


def _jwt_secret() -> str:
    global _warned_dev_secret
    secret = get_settings().jwt_secret.strip()
    if not secret:
        if not _warned_dev_secret:  # warn once per process, not on every token op
            log.warning("JWT_SECRET is blank — using the insecure dev key. Set JWT_SECRET in production.")
            _warned_dev_secret = True
        return _DEV_JWT_SECRET
    return secret


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


# --------------------------------------------------------------------------- #
# Passwords — bcrypt over a sha256 pre-hash.
# --------------------------------------------------------------------------- #

def _prehash(password: str) -> bytes:
    """sha256 → base64 (44 bytes, < bcrypt's 72-byte cap) so long passwords aren't truncated."""
    return base64.b64encode(hashlib.sha256(password.encode("utf-8")).digest())


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prehash(password), bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(_prehash(password), password_hash.encode("ascii"))
    except (ValueError, TypeError):
        return False


# --------------------------------------------------------------------------- #
# Session JWTs (HS256, with expiry).
# --------------------------------------------------------------------------- #

def create_session_token(user_id: str) -> str:
    now = _now()
    payload = {
        "sub": user_id,
        "type": "session",
        "iat": now,
        "exp": now + dt.timedelta(seconds=get_settings().jwt_expiry),
    }
    return jwt.encode(payload, _jwt_secret(), algorithm="HS256")


def decode_session_token(token: str) -> str | None:
    """Return the user id from a valid, unexpired session token, else None."""
    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    if payload.get("type") != "session":
        return None
    return payload.get("sub")


# --------------------------------------------------------------------------- #
# OTPs, random tokens, and at-rest hashing.
# --------------------------------------------------------------------------- #

def generate_otp() -> str:
    """A 6-digit numeric code (cryptographically random, zero-padded)."""
    return f"{secrets.randbelow(1_000_000):06d}"


def generate_token() -> str:
    """A high-entropy URL-safe secret for set-password / reset links."""
    return secrets.token_urlsafe(32)


def hash_secret(secret: str) -> str:
    """sha256 hex — what we store for OTPs / tokens. The plaintext is never persisted (Art. X)."""
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def expires_in(seconds: int) -> dt.datetime:
    return _now() + dt.timedelta(seconds=seconds)


def is_expired(expires_at) -> bool:
    """True if `expires_at` (datetime or ISO string) is in the past."""
    if isinstance(expires_at, str):
        # JSON registry stores e.g. "…+00:00" or "…Z"; normalize Z for pre-3.11 safety.
        expires_at = dt.datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=dt.timezone.utc)
    return _now() >= expires_at
