"""Auth flow tests (feature 002, tasks T124/T134): signup → OTP → set-password →
login, plus wrong OTP, expired/used tokens, unverified login, duplicate email, and
the Google new-vs-existing paths."""

from __future__ import annotations

import datetime as dt

import pytest

from tests.conftest import auth_headers


# --------------------------------------------------------------------------- #
# Happy path
# --------------------------------------------------------------------------- #

def test_signup_verify_setpassword_login_me(client, outbox):
    email = "aarav@example.com"
    assert client.post("/api/auth/signup", json={"email": email}).status_code == 200
    otp = outbox["otps"][email]

    r = client.post("/api/auth/verify-otp", json={"email": email, "otp": otp})
    assert r.status_code == 200
    spt = r.json()["set_password_token"]

    r = client.post("/api/auth/set-password", json={"token": spt, "password": "password123"})
    assert r.status_code == 200
    body = r.json()
    assert body["user"]["email"] == email
    assert body["user"]["email_verified"] is True
    assert "password" not in str(body)  # never echo a password/hash
    token = body["session_token"]

    r = client.get("/api/auth/me", headers=auth_headers(token))
    assert r.status_code == 200 and r.json()["email"] == email

    r = client.post("/api/auth/login", json={"email": email, "password": "password123"})
    assert r.status_code == 200 and "session_token" in r.json()


def test_login_is_case_insensitive_on_email(client, register):
    register("MixedCase@Example.com")
    r = client.post("/api/auth/login", json={"email": "mixedcase@example.com", "password": "password123"})
    assert r.status_code == 200


# --------------------------------------------------------------------------- #
# OTP failures
# --------------------------------------------------------------------------- #

def test_wrong_otp_rejected(client, outbox):
    email = "wrong@example.com"
    client.post("/api/auth/signup", json={"email": email})
    otp = outbox["otps"][email]
    wrong = f"{(int(otp) + 1) % 1_000_000:06d}"
    r = client.post("/api/auth/verify-otp", json={"email": email, "otp": wrong})
    assert r.status_code == 400 and r.json()["error"]["code"] == "invalid_otp"


def test_otp_attempt_limit_locks_code(client, outbox):
    email = "lock@example.com"
    client.post("/api/auth/signup", json={"email": email})
    otp = outbox["otps"][email]
    wrong = f"{(int(otp) + 1) % 1_000_000:06d}"
    for _ in range(5):  # OTP_MAX_ATTEMPTS
        client.post("/api/auth/verify-otp", json={"email": email, "otp": wrong})
    # even the correct code no longer works once locked out
    r = client.post("/api/auth/verify-otp", json={"email": email, "otp": otp})
    assert r.status_code == 400 and r.json()["error"]["code"] == "invalid_otp"


# --------------------------------------------------------------------------- #
# Token single-use / expiry
# --------------------------------------------------------------------------- #

def test_set_password_token_is_single_use(client, outbox):
    email = "single@example.com"
    client.post("/api/auth/signup", json={"email": email})
    otp = outbox["otps"][email]
    spt = client.post("/api/auth/verify-otp", json={"email": email, "otp": otp}).json()["set_password_token"]
    assert client.post("/api/auth/set-password", json={"token": spt, "password": "password123"}).status_code == 200
    # reusing the same token must fail (single-use)
    r = client.post("/api/auth/set-password", json={"token": spt, "password": "password456"})
    assert r.status_code == 400 and r.json()["error"]["code"] == "invalid_token"


def test_expired_reset_token_rejected(client, register):
    from app import store
    from app.auth import security
    from app.models import AuthToken, TokenKind

    user = register("expire@example.com")["user"]
    secret = "raw-reset-secret"
    store.create_auth_token(AuthToken(
        user_id=user["id"], kind=TokenKind.reset, token_hash=security.hash_secret(secret),
        expires_at=dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=1),
    ))
    r = client.post("/api/auth/reset-password", json={"token": secret, "password": "brandnew123"})
    assert r.status_code == 400 and r.json()["error"]["code"] == "invalid_token"


def test_weak_password_rejected(client, outbox):
    email = "weak@example.com"
    client.post("/api/auth/signup", json={"email": email})
    otp = outbox["otps"][email]
    spt = client.post("/api/auth/verify-otp", json={"email": email, "otp": otp}).json()["set_password_token"]
    r = client.post("/api/auth/set-password", json={"token": spt, "password": "short"})
    assert r.status_code == 400 and r.json()["error"]["code"] == "weak_password"


# --------------------------------------------------------------------------- #
# Login edge cases / enumeration
# --------------------------------------------------------------------------- #

def test_unverified_account_with_password_cannot_login(client):
    """The 403 'verify first' path: a user with a password but unverified email."""
    from app import store
    from app.auth import security
    from app.models import AuthProvider, User

    store.create_user(User(email="unv@example.com",
                           password_hash=security.hash_password("password123"),
                           email_verified=False, auth_provider=AuthProvider.local))
    r = client.post("/api/auth/login", json={"email": "unv@example.com", "password": "password123"})
    assert r.status_code == 403 and r.json()["error"]["code"] == "email_not_verified"


def test_login_unknown_email_and_wrong_password_are_indistinguishable(client, register):
    register("real@example.com")
    unknown = client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "password123"})
    wrong = client.post("/api/auth/login", json={"email": "real@example.com", "password": "wrongwrong"})
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json() == wrong.json()  # identical → no enumeration


def test_duplicate_signup_does_not_leak_or_duplicate(client, outbox):
    from app import store

    email = "dup@example.com"
    r1 = client.post("/api/auth/signup", json={"email": email})
    r2 = client.post("/api/auth/signup", json={"email": email})
    assert r1.status_code == r2.status_code == 200
    assert r1.json() == r2.json()  # same neutral message both times
    assert store.get_user_by_email(email) is not None  # the account exists (created once)


def test_invalid_email_rejected(client):
    r = client.post("/api/auth/signup", json={"email": "not-an-email"})
    assert r.status_code == 400 and r.json()["error"]["code"] == "invalid_email"


# --------------------------------------------------------------------------- #
# /me without / with bad token
# --------------------------------------------------------------------------- #

def test_me_requires_valid_token(client):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers=auth_headers("garbage.token.here")).status_code == 401


# --------------------------------------------------------------------------- #
# Forgot / reset
# --------------------------------------------------------------------------- #

def test_forgot_password_is_neutral_and_reset_works(client, register, outbox):
    register("reset@example.com", password="oldpassword1")
    r = client.post("/api/auth/forgot-password", json={"email": "reset@example.com"})
    assert r.status_code == 200
    # unknown email returns the identical neutral response (no enumeration)
    r2 = client.post("/api/auth/forgot-password", json={"email": "ghost@example.com"})
    assert r2.json() == r.json()

    _, url = outbox["resets"][-1]
    token = url.split("token=")[1]
    assert client.post("/api/auth/reset-password",
                       json={"token": token, "password": "newpassword2"}).status_code == 200
    # new password works, old one doesn't
    assert client.post("/api/auth/login",
                       json={"email": "reset@example.com", "password": "newpassword2"}).status_code == 200
    assert client.post("/api/auth/login",
                       json={"email": "reset@example.com", "password": "oldpassword1"}).status_code == 401


def test_reset_token_single_use(client, register, outbox):
    register("reuse@example.com")
    client.post("/api/auth/forgot-password", json={"email": "reuse@example.com"})
    token = outbox["resets"][-1][1].split("token=")[1]
    assert client.post("/api/auth/reset-password",
                       json={"token": token, "password": "firstnew12"}).status_code == 200
    r = client.post("/api/auth/reset-password", json={"token": token, "password": "secondnew12"})
    assert r.status_code == 400 and r.json()["error"]["code"] == "invalid_token"


# --------------------------------------------------------------------------- #
# Google sign-in (verifier mocked; real path is server-side cert verification)
# --------------------------------------------------------------------------- #

def test_google_not_configured_returns_503(client):
    # GOOGLE_OAUTH_CLIENT_ID is blank in tests → real verifier raises GoogleNotConfigured
    r = client.post("/api/auth/google", json={"id_token": "anything"})
    assert r.status_code == 503 and r.json()["error"]["code"] == "google_not_configured"


def test_google_new_then_existing_user(client, monkeypatch):
    monkeypatch.setattr("app.auth.google.verify_google_id_token",
                        lambda tok: {"sub": "google-sub-1", "email": "guser@example.com",
                                     "email_verified": True})
    r1 = client.post("/api/auth/google", json={"id_token": "t1"})
    assert r1.status_code == 200
    u1 = r1.json()["user"]
    assert u1["email"] == "guser@example.com" and u1["auth_provider"] == "google"

    r2 = client.post("/api/auth/google", json={"id_token": "t2"})
    assert r2.status_code == 200
    assert r2.json()["user"]["id"] == u1["id"]  # same account, not a duplicate


def test_invalid_google_token_returns_400(client, monkeypatch):
    from app.auth import google as google_mod

    def boom(tok):
        raise google_mod.GoogleAuthError("bad signature")

    monkeypatch.setattr("app.auth.google.verify_google_id_token", boom)
    r = client.post("/api/auth/google", json={"id_token": "forged"})
    assert r.status_code == 400 and r.json()["error"]["code"] == "invalid_google_token"
