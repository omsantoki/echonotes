"""Test fixtures for the auth + multi-tenancy suite (feature 002).

CRITICAL: the repo's real backend/.env points at live cloud services (Supabase
Postgres, Qdrant, S3, OpenAI). We override the relevant env vars HERE, before any
app module is imported, so the whole suite runs against a throwaway local JSON
registry in a temp dir and never reads, writes, or bills a production service.
"""

from __future__ import annotations

import os
import pathlib
import tempfile

# --- force local, isolated backends BEFORE importing app.* ---
_TMP = tempfile.mkdtemp(prefix="echonotes_test_")
os.environ.update({
    # storage: local JSON registry + local Chroma + local disk (no cloud)
    "DATABASE_URL": "",
    "QDRANT_URL": "",
    "CHROMA_HTTP_URL": "",
    "S3_BUCKET": "",
    "DATA_DIR": _TMP,
    "CHROMA_DIR": str(pathlib.Path(_TMP) / ".chroma"),
    # provider local so no OpenAI call is attempted (tests never invoke the pipeline)
    "PROVIDER": "local",
    # async: force INLINE + no broker so the suite is hermetic regardless of what the
    # real .env declares (it sets a live REDIS_URL + TASK_ALWAYS_EAGER=false). Without
    # this, active_async() resolves to "celery" here and the inline-mode startup-recovery
    # test silently flips to celery behavior. Mode-specific tests override via monkeypatch
    # (e.g. test_lifespan_leaves_orphans_in_celery_mode); the semantic-cache tests inject
    # fakeredis by patching cache._redis, so cache="off" here does not affect them.
    "REDIS_URL": "",
    "TASK_ALWAYS_EAGER": "true",
    # auth: deterministic dev settings; SMTP/Google blank → console + 503 fallbacks
    "JWT_SECRET": "test-secret-key-not-for-production",
    "JWT_EXPIRY": "3600",
    "OTP_TTL": "600",
    "OTP_MAX_ATTEMPTS": "5",
    "RESET_TOKEN_TTL": "3600",
    "FRONTEND_URL": "http://localhost:5173",
    "BOOTSTRAP_ADMIN_EMAIL": "admin@echonotes.local",
    "SMTP_HOST": "",
    "GOOGLE_OAUTH_CLIENT_ID": "",
})

import pytest  # noqa: E402

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()  # drop anything cached from the real .env during collection


@pytest.fixture(autouse=True)
def _isolate():
    """Reset settings cache + registry before every test so each starts hermetic and
    clean (covers tests that use `store` directly, not just the `client` fixture, and
    re-reads any env a test monkeypatched)."""
    get_settings.cache_clear()
    reg = pathlib.Path(_TMP) / "registry.json"
    if reg.exists():
        reg.unlink()
    yield


@pytest.fixture
def client():
    """A fresh TestClient with an empty registry (clean tenant slate per test)."""
    from fastapi.testclient import TestClient

    reg = pathlib.Path(_TMP) / "registry.json"
    if reg.exists():
        reg.unlink()

    from app.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture
def outbox(monkeypatch):
    """Capture OTP codes + reset links instead of sending email (service emails the
    plaintext exactly once; the stored token is only a hash, so this is the sole way
    to learn the OTP — mirroring the dev console fallback)."""
    sent = {"otps": {}, "resets": []}

    def fake_otp(to: str, otp: str) -> None:
        sent["otps"][to.lower()] = otp

    def fake_reset(to: str, url: str) -> None:
        sent["resets"].append((to.lower(), url))

    monkeypatch.setattr("app.email.send_otp_email", fake_otp)
    monkeypatch.setattr("app.email.send_reset_email", fake_reset)
    return sent


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def register(client, outbox):
    """Run the full signup→OTP→set-password flow and return {session_token, user}."""
    def _register(email: str, password: str = "password123") -> dict:
        assert client.post("/api/auth/signup", json={"email": email}).status_code == 200
        otp = outbox["otps"][email.lower()]
        r = client.post("/api/auth/verify-otp", json={"email": email, "otp": otp})
        assert r.status_code == 200, r.text
        spt = r.json()["set_password_token"]
        r = client.post("/api/auth/set-password", json={"token": spt, "password": password})
        assert r.status_code == 200, r.text
        return r.json()

    return _register
