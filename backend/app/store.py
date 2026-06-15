"""Persistence facade (task T004).

`store` is the stable public API the rest of the app imports — nothing else
touches storage. Underneath, three pluggable backends are selected by config,
mirroring the provider switch in embed.py / transcribe.py:

  * vectors   — local Chroma  → Qdrant / remote Chroma   (QDRANT_URL / CHROMA_HTTP_URL)
  * registry  — registry.json → managed Postgres          (DATABASE_URL)
  * objects   — local disk    → object storage (R2/S3)     (S3_BUCKET)

With all those env vars blank, behavior is byte-identical to the all-local
build, so local dev needs zero cloud services (Art. VIII, IX). Audio/PDF are
still never persisted (Art. IV) — that lives in the pipeline, untouched.

This facade keeps three things itself so no backend can diverge on them:
the `add_chunks` validation guards (Art. II/III/VI), `assemble_document`, and
the cross-store cascade in `delete_lecture` / `delete_course`.
"""

from __future__ import annotations

from functools import lru_cache

from app.config import get_settings
from app.models import (AuthToken, Course, DiagramAsset, Lecture, LectureStatus,
                        NoteChunk, TokenKind, User)


# --------------------------------------------------------------------------- #
# Backend selection — lazy imports so a local install needs no cloud SDKs.
# --------------------------------------------------------------------------- #

@lru_cache
def _vectors():
    s = get_settings()
    if s.qdrant_url:
        from app.storage.vectors_qdrant import QdrantVectors
        return QdrantVectors()
    if s.chroma_http_url:
        from app.storage.vectors_chroma import RemoteChromaVectors
        return RemoteChromaVectors()
    from app.storage.vectors_chroma import LocalChromaVectors
    return LocalChromaVectors()


@lru_cache
def _registry():
    if get_settings().database_url:
        from app.storage.registry_pg import PostgresRegistry
        return PostgresRegistry()
    from app.storage.registry_json import JsonRegistry
    return JsonRegistry()


@lru_cache
def _objects():
    if get_settings().s3_bucket:
        from app.storage.objects_s3 import S3Objects
        return S3Objects()
    from app.storage.objects_local import LocalObjects
    return LocalObjects()


# --------------------------------------------------------------------------- #
# NoteChunks (vectors + metadata)
# --------------------------------------------------------------------------- #

def add_chunks(chunks: list[NoteChunk]) -> None:
    """Persist NoteChunks (text + embedding + metadata) per course/lecture.

    Validation lives here so every vector backend enforces Art. II/III/VI.
    """
    chunks = [c for c in chunks if c.text.strip()]
    if not chunks:
        return
    for c in chunks:
        if c.embedding is None:
            raise ValueError(f"NoteChunk {c.id} has no embedding (Art. VI).")
        if not c.reason or not c.source_type:
            raise ValueError(f"NoteChunk {c.id} missing source_type/reason (Art. II/III).")
    _vectors().add(chunks)


def query(course_id: str, query_embedding: list[float], n: int = 5,
          exclude_lecture_id: str | None = None) -> list[dict]:
    """Similarity search within a course (search + cross-lecture retrieval).

    `exclude_lecture_id` drops one lecture's own chunks — used so a lecture links to
    OTHER lectures, never to itself (Stretch). Backends return `distance` (cosine
    distance, smaller = closer); retrieve.py converts that to similarity.
    """
    return _vectors().query(course_id, query_embedding, n, exclude_lecture_id)


def update_chunk_text(chunk_id: str, text: str, embedding: list[float]) -> None:
    """Replace a stored chunk's text + embedding (e.g. backfilling a diagram
    description so it becomes the searchable text + caption — T030/US-5)."""
    _vectors().update_text(chunk_id, text, embedding)


def list_chunks(lecture_id: str) -> list[dict]:
    """All chunks for a lecture, ordered, for rendering the merged document."""
    return _vectors().list_by_lecture(lecture_id)


def assemble_document(lecture_id: str) -> dict:
    """Build the topic->segments document (GET /api/lectures/{id} ready shape).

    Segments are grouped by topic in document order; rendered, they read as one
    flowing narrative. Every segment carries its source label + reason (Art. II,
    III) straight from the stored metadata, and a `spoken_only` flag so the UI can
    emphasize spoken-only passages inline.
    """
    rows = list_chunks(lecture_id)
    links = (get_lecture(lecture_id) or {}).get("links", {}) or {}  # Stretch (T041)
    topics: list[dict] = []
    by_topic: dict[str, dict] = {}
    for row in rows:
        meta = row["metadata"]
        topic = meta.get("topic", "Notes")
        if topic not in by_topic:
            by_topic[topic] = {"topic": topic, "segments": []}
            topics.append(by_topic[topic])
        reason = str(meta.get("reason", ""))
        diagram_ref = meta.get("diagram_ref")
        # Resolve the preserved image URL so the JSON API is self-contained — the
        # React frontend renders the figure straight from the document, with no
        # extra per-diagram fetch (an "/assets/…" path locally, an absolute URL in prod).
        image_ref = None
        if diagram_ref:
            asset = get_diagram(diagram_ref)
            image_ref = asset.get("image_ref") if asset else None
        by_topic[topic]["segments"].append({
            "source_type": meta.get("source_type"),
            "text": row["text"],
            "reason": reason,
            "confidence": meta.get("confidence", 0.0),
            "spoken_only": meta.get("source_type") == "spoken" and reason.startswith("★ Spoken-only"),
            "diagram_ref": diagram_ref,
            "image_ref": image_ref,
        })
    for topic in topics:
        if topic["topic"] in links:
            topic["builds_on"] = links[topic["topic"]]  # cross-lecture "builds on" (Stretch)
    return {"topics": topics}


# --------------------------------------------------------------------------- #
# Users & auth tokens (feature 002, Art. X) — structural registry rows.
# Secrets are hashed before they reach here (see app/auth/security.py); this
# facade never sees or stores a plaintext password, OTP, or token.
# --------------------------------------------------------------------------- #

def create_user(user: User) -> User:
    return _registry().create_user(user)


def get_user(user_id: str) -> dict | None:
    return _registry().get_user(user_id)


def get_user_by_email(email: str) -> dict | None:
    return _registry().get_user_by_email(email)


def get_user_by_google_sub(google_sub: str) -> dict | None:
    return _registry().get_user_by_google_sub(google_sub)


def update_user(user_id: str, changes: dict) -> None:
    _registry().update_user(user_id, changes)


def create_auth_token(token: AuthToken) -> AuthToken:
    return _registry().create_auth_token(token)


def find_auth_token(kind: TokenKind, *, user_id: str | None = None,
                    token_hash: str | None = None) -> dict | None:
    return _registry().find_auth_token(kind, user_id=user_id, token_hash=token_hash)


def bump_auth_token(token_id: str, *, attempts: int | None = None,
                    used: bool | None = None) -> None:
    _registry().bump_auth_token(token_id, attempts=attempts, used=used)


def invalidate_auth_tokens(user_id: str, kind: TokenKind) -> None:
    """Mark every prior token of this kind used, so an old OTP/link can't be replayed."""
    _registry().invalidate_auth_tokens(user_id, kind)


# --------------------------------------------------------------------------- #
# Course / Lecture registry (structural, not vectors)
#
# `owner_id` scopes reads/lists/deletes to the caller (feature 002, Art. X). The
# filter is enforced in the registry backend, not here. `owner_id=None` is the
# internal/system path (pipeline, startup recovery) with no owner filter.
# --------------------------------------------------------------------------- #

def create_course(course: Course) -> Course:
    return _registry().create_course(course)


def list_courses(owner_id: str | None = None) -> list[dict]:
    return _registry().list_courses(owner_id)


def get_course(course_id: str, owner_id: str | None = None) -> dict | None:
    return _registry().get_course(course_id, owner_id)


def create_lecture(lecture: Lecture) -> Lecture:
    return _registry().create_lecture(lecture)


def get_lecture(lecture_id: str, owner_id: str | None = None) -> dict | None:
    return _registry().get_lecture(lecture_id, owner_id)


def list_lectures(course_id: str) -> list[dict]:
    return _registry().list_lectures(course_id)


def list_all_lectures() -> list[dict]:
    """Every lecture across all owners — system path only (startup recovery scan)."""
    return _registry().list_all_lectures()


def update_lecture(lecture_id: str, *, status: LectureStatus | None = None,
                   progress: str | None = None) -> None:
    _registry().update_lecture(lecture_id, status, progress)


def set_lecture_links(lecture_id: str, links: dict) -> None:
    """Persist cross-lecture 'builds on' links per topic (Stretch, T041)."""
    _registry().set_lecture_links(lecture_id, links)


# --------------------------------------------------------------------------- #
# Diagram assets — preserved slide images (registry rows + stored bytes)
# --------------------------------------------------------------------------- #

def save_diagram_image(lecture_id: str, asset_id: str, ext: str, data: bytes) -> str:
    """Store a preserved diagram image and return its reference (a "/assets/…"
    path locally, or an absolute object-storage URL in production)."""
    return _objects().save_diagram_image(lecture_id, asset_id, ext, data)


def read_diagram_bytes(asset: dict) -> bytes | None:
    """Read back a stored diagram image (used by the description backfill)."""
    return _objects().read_diagram_bytes(asset)


def create_diagram(asset: DiagramAsset) -> DiagramAsset:
    return _registry().create_diagram(asset)


def get_diagram(asset_id: str) -> dict | None:
    return _registry().get_diagram(asset_id)


def list_diagrams(lecture_id: str) -> list[dict]:
    return _registry().list_diagrams(lecture_id)


def list_all_diagrams() -> list[dict]:
    return _registry().list_all_diagrams()


# --------------------------------------------------------------------------- #
# Cross-store deletes — orchestrated here because they span all three backends.
# --------------------------------------------------------------------------- #

def delete_lecture(lecture_id: str, owner_id: str | None = None) -> bool:
    """Delete a lecture and everything it owns: its NoteChunk vectors, its
    preserved diagram images, and its registry rows. Returns False if the lecture
    does not exist OR is not owned by `owner_id` (when given) — so a non-owner sees
    the same "not found" as a missing lecture (Art. X). Idempotent / best-effort."""
    if not _registry().delete_lecture_rows(lecture_id, owner_id):
        return False
    try:
        _vectors().delete_by_lecture(lecture_id)
    except Exception:
        pass
    _objects().delete_lecture_assets(lecture_id)
    return True


def delete_course(course_id: str, owner_id: str | None = None) -> bool:
    """Delete a course and cascade-delete all of its lectures. Returns False if the
    course does not exist OR is not owned by `owner_id` (when given) — non-owners get
    the same "not found" (Art. X). Ownership is checked once here; the cascade then
    deletes the now-confirmed-owned lectures internally."""
    if _registry().get_course(course_id, owner_id) is None:
        return False
    for lid in _registry().list_lecture_ids(course_id):
        delete_lecture(lid)  # ownership already confirmed at the course level
    _registry().delete_course_row(course_id, owner_id)
    return True
