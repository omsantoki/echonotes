"""Unit tests for the auth crypto primitives (security.py) and the email sender
(email.py) — both core to Constitution Art. X (no plaintext secrets; local-dev
console fallback)."""

from __future__ import annotations

import datetime as dt
import logging

from app import email as email_mod
from app.auth import security


# --- passwords ------------------------------------------------------------ #

def test_password_hash_roundtrip():
    h = security.hash_password("correct horse battery staple")
    assert h != "correct horse battery staple"  # never stored in the clear
    assert security.verify_password("correct horse battery staple", h) is True
    assert security.verify_password("wrong", h) is False
    assert security.verify_password("anything", None) is False  # google-only account


def test_long_password_not_truncated_by_bcrypt():
    # The sha256 pre-hash means two long passwords that differ only past bcrypt's
    # 72-byte cap must still produce DIFFERENT hashes (no silent truncation).
    base = "a" * 80
    h = security.hash_password(base + "X")
    assert security.verify_password(base + "X", h) is True
    assert security.verify_password(base + "Y", h) is False


# --- session JWT ---------------------------------------------------------- #

def test_session_token_roundtrip_and_rejects_garbage():
    tok = security.create_session_token("user-123")
    assert security.decode_session_token(tok) == "user-123"
    assert security.decode_session_token("not-a-jwt") is None
    assert security.decode_session_token(tok + "tamper") is None


# --- OTP / token hashing -------------------------------------------------- #

def test_otp_is_six_digits():
    for _ in range(20):
        otp = security.generate_otp()
        assert len(otp) == 6 and otp.isdigit()


def test_hash_secret_deterministic_and_tokens_unique():
    assert security.hash_secret("x") == security.hash_secret("x")
    assert security.hash_secret("x") != security.hash_secret("y")
    assert security.generate_token() != security.generate_token()


def test_is_expired_handles_z_suffix_past_and_future():
    past = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    future = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1)).isoformat()
    assert security.is_expired(past) is True
    assert security.is_expired(future) is False


# --- email: console fallback + SMTP path ---------------------------------- #

def test_email_console_fallback_when_smtp_unconfigured(caplog):
    # SMTP is blank in the test env → the OTP/link is logged, not sent (and never raises).
    with caplog.at_level(logging.WARNING, logger="echonotes.email"):
        email_mod.send_email("to@x.com", "Subject", "your code is 654321")
    assert any("654321" in r.getMessage() for r in caplog.records)


def test_email_smtp_send_path(monkeypatch):
    from app.config import get_settings
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_USER", "u@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "key")
    monkeypatch.setenv("SMTP_FROM", "from@example.com")
    get_settings.cache_clear()

    sent: dict = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout=None):
            sent["host"], sent["port"] = host, port

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def ehlo(self):
            pass

        def starttls(self):
            pass

        def login(self, user, pw):
            sent["login"] = (user, pw)

        def send_message(self, msg):
            sent["to"], sent["from"] = msg["To"], msg["From"]

    monkeypatch.setattr(email_mod.smtplib, "SMTP", FakeSMTP)
    email_mod.send_email("to@x.com", "S", "B")

    assert sent["host"] == "smtp.example.com" and sent["port"] == 587
    assert sent["login"] == ("u@example.com", "key")
    assert sent["to"] == "to@x.com" and sent["from"] == "from@example.com"


def test_email_send_failure_falls_back_to_console(monkeypatch, caplog):
    from app.config import get_settings
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_USER", "u@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "key")
    get_settings.cache_clear()

    def boom(*a, **k):
        raise OSError("connection refused")

    monkeypatch.setattr(email_mod.smtplib, "SMTP", boom)
    with caplog.at_level(logging.WARNING, logger="echonotes.email"):
        email_mod.send_email("to@x.com", "S", "fallback code 111222")  # must not raise
    assert any("111222" in r.getMessage() for r in caplog.records)
