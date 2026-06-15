"""Transactional email (feature 002): OTP codes and password-reset links.

Mirrors the repo's "blank env = local dev" philosophy (Art. VIII/IX): if SMTP is
not configured, the message is printed to the server log instead of sent, so local
dev needs **no** mail server. Credentials come from env only and are never logged
(Art. X) — the only thing the console fallback prints is the dev OTP / reset link,
which is the intended, documented behavior for local development.

Gmail works with an App Password (https://myaccount.google.com/apppasswords) — set
SMTP_HOST=smtp.gmail.com, SMTP_USER, SMTP_PASSWORD (the App Password), SMTP_FROM.
"""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.config import get_settings

log = logging.getLogger("echonotes.email")


def _smtp_configured() -> bool:
    return bool(get_settings().smtp_host.strip())


def send_email(to: str, subject: str, body: str) -> None:
    """Send a plain-text email, or print it to the log when SMTP is unconfigured.

    Never raises on a send failure — auth flows that email the user (signup,
    forgot-password) must not 500 because the mail server hiccuped; the dev console
    fallback always works. Failures are logged (without any secret).
    """
    s = get_settings()
    if not _smtp_configured():
        # Local-dev fallback: the body carries the OTP / reset link — print it so the
        # developer can complete the flow with no mail server (documented behavior).
        log.warning("[email:console] To:%s | %s\n%s", to, subject, body)
        return

    sender = (s.smtp_from or s.smtp_user or "no-reply@echonotes.local").strip()
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    try:
        with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=15) as smtp:
            smtp.ehlo()
            try:
                smtp.starttls()
                smtp.ehlo()
            except smtplib.SMTPException:
                pass  # server may not support STARTTLS (e.g. localhost test relay)
            if s.smtp_user:
                smtp.login(s.smtp_user, s.smtp_password)
            smtp.send_message(msg)
    except Exception as exc:  # never let mail trouble break the auth flow
        log.error("SMTP send to %s failed: %s", to, exc)


def send_otp_email(to: str, otp: str) -> None:
    """Email the 6-digit signup verification code."""
    send_email(
        to,
        "Your EchoNotes verification code",
        f"Welcome to EchoNotes!\n\nYour verification code is: {otp}\n\n"
        f"It expires in {get_settings().otp_ttl // 60} minutes. "
        "If you didn't request this, you can ignore this email.",
    )


def send_reset_email(to: str, reset_url: str) -> None:
    """Email the password-reset link."""
    send_email(
        to,
        "Reset your EchoNotes password",
        f"We received a request to reset your EchoNotes password.\n\n"
        f"Open this link to choose a new one:\n{reset_url}\n\n"
        f"The link expires in {get_settings().reset_token_ttl // 60} minutes. "
        "If you didn't request this, you can safely ignore this email.",
    )
