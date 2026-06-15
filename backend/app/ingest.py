"""Ingestion (task T010): accept + validate uploads, then launch the pipeline.

Audio and slides are written to a private temp workspace and the pipeline deletes
that workspace (and the audio inside it) when it finishes (Art. IV). Both the JSON
API and the web form go through here, so there is exactly one ingestion path.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import BackgroundTasks, HTTPException, UploadFile

from app import store
from app.models import Lecture, LectureStatus
from app.pipeline import run_pipeline

_AUDIO_EXTS = {".mp3", ".m4a", ".wav", ".flac", ".ogg", ".webm", ".mp4", ".mpeg", ".mpga", ".aac"}
_MAX_BYTES = 500 * 1024 * 1024  # 500 MB guard rail


async def create_and_launch_lecture(course_id: str, title: str, audio: UploadFile,
                                    slides: UploadFile, bg: BackgroundTasks) -> Lecture:
    if not store.get_course(course_id):
        raise HTTPException(404, detail={"code": "course_not_found",
                                         "message": f"No course {course_id}."})
    _require_ext(audio.filename, _AUDIO_EXTS, "audio")
    _require_ext(slides.filename, {".pdf"}, "slides (PDF)")

    workdir = Path(tempfile.mkdtemp(prefix="echonotes_"))
    audio_path = workdir / f"audio{_ext(audio.filename)}"
    pdf_path = workdir / "slides.pdf"
    await _save(audio, audio_path)
    await _save(slides, pdf_path)

    lecture = Lecture(course_id=course_id, title=title or "Untitled lecture",
                      status=LectureStatus.processing, progress="Queued…")
    store.create_lecture(lecture)
    bg.add_task(run_pipeline, lecture.id, course_id, str(audio_path),
                str(pdf_path), str(workdir))
    return lecture


async def _save(upload: UploadFile, dest: Path) -> None:
    size = 0
    with dest.open("wb") as fh:
        while chunk := await upload.read(1024 * 1024):
            size += len(chunk)
            if size > _MAX_BYTES:
                raise HTTPException(413, detail={"code": "file_too_large",
                                                 "message": "Upload exceeds 500 MB."})
            fh.write(chunk)


def _ext(name: str | None) -> str:
    return Path(name or "").suffix.lower() or ".bin"


def _require_ext(name: str | None, allowed: set[str], kind: str) -> None:
    if _ext(name) not in allowed:
        raise HTTPException(400, detail={"code": "bad_upload",
            "message": f"Unsupported {kind} file type: {name!r}."})
