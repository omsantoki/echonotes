"""Data model (task T003) — mirrors specs/.../data-model.md exactly.

Storage is embeddings-first: the vector store holds NoteChunks; Course/Lecture
are a tiny registry. There is deliberately **no Audio entity** (Constitution
Art. IV — raw audio is processed in temp and discarded).
"""

from __future__ import annotations

import datetime as dt
import uuid
from enum import Enum

from pydantic import BaseModel, Field


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class LectureStatus(str, Enum):
    uploaded = "uploaded"
    processing = "processing"
    ready = "ready"
    failed = "failed"


class SourceType(str, Enum):
    """Provenance of a note block — sacred, never optional (Art. III)."""

    slides = "slides"
    spoken = "spoken"
    diagram = "diagram"


class AuthProvider(str, Enum):
    """How an account was created / how it signs in (002, Art. X)."""

    local = "local"    # email + password (verified by OTP)
    google = "google"  # Google sign-in (no password unless one is set via reset)


class TokenKind(str, Enum):
    """Short-lived, single-use auth credentials — stored hashed (002, Art. X)."""

    otp = "otp"                    # 6-digit email verification code
    set_password = "set_password"  # issued after OTP verify; lets a verified user set a password
    reset = "reset"                # emailed forgot-password reset link token


class User(BaseModel):
    """An account owner (feature 002). Email is the unique, lowercased identity.

    `password_hash` is None for Google-only accounts until they set one. Secrets are
    never stored in plaintext (Art. X) — see app/auth/security.py for hashing.
    """

    id: str = Field(default_factory=_uuid)
    email: str                              # unique; ALWAYS normalized lowercase before store/compare
    password_hash: str | None = None        # bcrypt(sha256(password)); None for Google-only accounts
    email_verified: bool = False
    auth_provider: AuthProvider = AuthProvider.local
    google_sub: str | None = None            # Google subject id (set for google accounts)
    created_at: dt.datetime = Field(default_factory=_now)

    def public(self) -> dict:
        """The user shape safe to return over the API — never the password hash (Art. X)."""
        return {
            "id": self.id,
            "email": self.email,
            "auth_provider": self.auth_provider.value,
            "email_verified": self.email_verified,
            "created_at": self.created_at.isoformat(),
        }


class AuthToken(BaseModel):
    """A hashed, short-TTL, single-use credential (OTP / set-password / reset; Art. X).

    Only the sha256 hash of the secret is stored; the plaintext is emailed/returned once.
    """

    id: str = Field(default_factory=_uuid)
    user_id: str
    kind: TokenKind
    token_hash: str            # sha256 of the OTP / random token — never the plaintext
    expires_at: dt.datetime
    attempts: int = 0          # failed checks (OTP brute-force guard)
    used: bool = False         # single-use: a consumed token is rejected
    created_at: dt.datetime = Field(default_factory=_now)


class Course(BaseModel):
    id: str = Field(default_factory=_uuid)
    name: str
    owner_id: str | None = None  # FK -> User (002, Art. X). None only for pre-002 legacy rows.
    created_at: dt.datetime = Field(default_factory=_now)


class Lecture(BaseModel):
    id: str = Field(default_factory=_uuid)
    course_id: str
    title: str
    date: dt.date | None = None
    status: LectureStatus = LectureStatus.uploaded
    progress: str = ""  # human-readable progress for the polling UI
    created_at: dt.datetime = Field(default_factory=_now)


class DiagramAsset(BaseModel):
    id: str = Field(default_factory=_uuid)
    lecture_id: str
    image_ref: str           # stored image location/key
    section_topic: str       # which topic it belongs to
    description: str | None = None  # (Strong) vision-generated description


class NoteChunk(BaseModel):
    """The core unit — stored with its embedding in the vector store."""

    id: str = Field(default_factory=_uuid)
    lecture_id: str
    course_id: str               # denormalized for course-wide search (Art. V)
    topic: str                   # section/topic heading
    order: int                   # position within the lecture document
    text: str
    source_type: SourceType      # slides | spoken | diagram (Art. III)
    reason: str                  # explainability: WHY placed/labeled here (Art. II)
    confidence: float = 1.0      # alignment confidence (0-1)
    diagram_ref: str | None = None      # FK -> DiagramAsset when source_type=diagram
    embedding: list[float] | None = None  # from the single embedding model (Art. VI)
    links_to: list[str] | None = None     # (Stretch) earlier chunks this builds on

    def metadata(self) -> dict:
        """Mandatory metadata stored alongside the vector (Art. III, V)."""
        meta = {
            "chunk_id": self.id,
            "lecture_id": self.lecture_id,
            "course_id": self.course_id,
            "topic": self.topic,
            "source_type": self.source_type.value,
            "order": self.order,
            "confidence": self.confidence,
            # `reason` is beyond the data-model's mandated metadata set, but the
            # API contract returns it per block (Art. II explainability) and we
            # only persist notes, so it must live with the vector.
            "reason": self.reason,
        }
        if self.diagram_ref:
            meta["diagram_ref"] = self.diagram_ref
        return meta
