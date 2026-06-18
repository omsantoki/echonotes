"""Request schemas for /api/auth/* (feature 002).

Email is a plain `str` (validated/normalized in service.py) to avoid pulling in the
`email-validator` dependency that pydantic's EmailStr requires. Responses are plain
dicts built by the service so we control exactly what is returned (never a hash/token).
"""

from __future__ import annotations

from pydantic import BaseModel


class SignupIn(BaseModel):
    email: str


class VerifyOtpIn(BaseModel):
    email: str
    otp: str


class SetPasswordIn(BaseModel):
    token: str
    password: str


class LoginIn(BaseModel):
    email: str
    password: str


class GoogleIn(BaseModel):
    id_token: str


class ForgotPasswordIn(BaseModel):
    email: str


class ResetPasswordIn(BaseModel):
    token: str
    password: str
