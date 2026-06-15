"""Auth endpoints (feature 002): /api/auth/* — see
specs/002-accounts-multitenancy/contracts/api.md.

Thin router: all logic lives in service.py; the only authenticated endpoint here
is GET /api/auth/me (via get_current_user). Errors raised by the service use the
{"code","message"} detail shape, which main.py wraps in the standard envelope.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth import service
from app.auth.deps import get_current_user
from app.auth.schemas import (ForgotPasswordIn, GoogleIn, LoginIn, ResetPasswordIn,
                              SetPasswordIn, SignupIn, VerifyOtpIn)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/signup")
def signup(body: SignupIn):
    return service.signup(body.email)


@router.post("/verify-otp")
def verify_otp(body: VerifyOtpIn):
    return service.verify_otp(body.email, body.otp)


@router.post("/set-password")
def set_password(body: SetPasswordIn):
    return service.set_password(body.token, body.password)


@router.post("/login")
def login(body: LoginIn):
    return service.login(body.email, body.password)


@router.post("/google")
def google(body: GoogleIn):
    return service.google_auth(body.id_token)


@router.post("/forgot-password")
def forgot_password(body: ForgotPasswordIn):
    return service.forgot_password(body.email)


@router.post("/reset-password")
def reset_password(body: ResetPasswordIn):
    return service.reset_password(body.token, body.password)


@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    return service._public_user(user)
