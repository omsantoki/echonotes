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


class Course(BaseModel):
    id: str = Field(default_factory=_uuid)
    name: str
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
