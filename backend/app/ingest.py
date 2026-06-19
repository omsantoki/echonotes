"""Ingestion (task T010): accept + validate uploads, then launch the pipeline.

Audio and slides are written to a private temp workspace and the pipeline deletes
that workspace (and the audio inside it) when it finishes (Art. IV). Both the JSON
API and the web form go through here, so there is exactly one ingestion path.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app import store
from app.models import Lecture, LectureStatus
from app.tasks import process_lecture

_AUDIO_EXTS = {".mp3", ".m4a", ".wav", ".flac", ".ogg", ".webm", ".mp4", ".mpeg", ".mpga", ".aac"}
_MAX_BYTES = 500 * 1024 * 1024  # 500 MB guard rail


async def create_and_launch_lecture(course_id: str, title: str, audio: UploadFile,
                                    slides: UploadFile,
                                    owner_id: str | None = None) -> Lecture:
    # Owner-scoped lookup: a course the caller doesn't own reads as "not found" (Art. X),
    # so uploading to someone else's course returns 404, not 403.
    if not store.get_course(course_id, owner_id=owner_id):
        raise HTTPException(404, detail={"code": "course_not_found",
                                         "message": f"No course {course_id}."})
    _require_ext(audio.filename, _AUDIO_EXTS, "audio")
    _require_ext(slides.filename, {".pdf"}, "slides (PDF)")

    lecture = Lecture(course_id=course_id, title=title or "Untitled lecture",
                      status=LectureStatus.processing, progress="Queued…")
    store.create_lecture(lecture)

    # Stream both uploads into SHARED storage (object backend) so a separate worker
    # host can read them — not a local temp dir the worker can't see. We name them
    # deterministically per lecture; the worker downloads them by name.
    audio_name = f"audio{_ext(audio.filename)}"
    pdf_name = "slides.pdf"
    await _save_to_store(audio, lecture.id, audio_name)
    await _save_to_store(slides, lecture.id, pdf_name)

    # Enqueue the heavy pipeline onto the Celery queue and return immediately. In dev/test
    # (task_always_eager) this runs inline; in prod a separate worker picks it up.
    process_lecture.delay(lecture.id, course_id, audio_name, pdf_name)
    return lecture


async def _save_to_store(upload: UploadFile, lecture_id: str, name: str) -> None:
    """Stream an upload to a size-guarded local temp file, then hand it to shared
    storage and remove the temp copy (so nothing accumulates on the web host)."""
    tmp = Path(tempfile.mkdtemp(prefix="echonotes_up_")) / name
    try:
        size = 0
        with tmp.open("wb") as fh:
            while chunk := await upload.read(1024 * 1024):
                size += len(chunk)
                if size > _MAX_BYTES:
                    raise HTTPException(413, detail={"code": "file_too_large",
                                                     "message": "Upload exceeds 500 MB."})
                fh.write(chunk)
        store.save_upload(lecture_id, name, str(tmp))
    finally:
        shutil.rmtree(tmp.parent, ignore_errors=True)


def _ext(name: str | None) -> str:
    return Path(name or "").suffix.lower() or ".bin"


def _require_ext(name: str | None, allowed: set[str], kind: str) -> None:
    if _ext(name) not in allowed:
        raise HTTPException(400, detail={"code": "bad_upload",
            "message": f"Unsupported {kind} file type: {name!r}."})
