"""Direct unit tests for Google ID-token verification (auth/google.py). The JWKS
client + jwt.decode are stubbed so the issuer/audience/claim checks are exercised
offline (no network, no real Google certs)."""

from __future__ import annotations

import pytest

from app.auth import google
from app.config import get_settings


class _FakeKey:
    key = "signing-key"


class _FakeJWK:
    def get_signing_key_from_jwt(self, _token):
        return _FakeKey()


def _configure(monkeypatch, client_id="client-123.apps.googleusercontent.com"):
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", client_id)
    get_settings.cache_clear()
    monkeypatch.setattr(google, "_jwk_client", _FakeJWK())  # bypass the network fetch


def test_verify_success_normalizes_email(monkeypatch):
    _configure(monkeypatch)
    monkeypatch.setattr(google.jwt, "decode", lambda *a, **k: {
        "iss": "https://accounts.google.com", "sub": "g-1",
        "email": "Person@Example.com", "email_verified": True,
    })
    claims = google.verify_google_id_token("tok")
    assert claims == {"sub": "g-1", "email": "person@example.com", "email_verified": True}


def test_verify_rejects_bad_issuer(monkeypatch):
    _configure(monkeypatch)
    monkeypatch.setattr(google.jwt, "decode", lambda *a, **k: {
        "iss": "https://evil.example", "sub": "x", "email": "e@x.com",
    })
    with pytest.raises(google.GoogleAuthError):
        google.verify_google_id_token("tok")


def test_verify_rejects_missing_email(monkeypatch):
    _configure(monkeypatch)
    monkeypatch.setattr(google.jwt, "decode", lambda *a, **k: {
        "iss": "accounts.google.com", "sub": "x",
    })
    with pytest.raises(google.GoogleAuthError):
        google.verify_google_id_token("tok")


def test_not_configured_raises(monkeypatch):
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "")
    get_settings.cache_clear()
    with pytest.raises(google.GoogleNotConfigured):
        google.verify_google_id_token("tok")
