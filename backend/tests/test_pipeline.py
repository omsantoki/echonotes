"""Pipeline orchestration tests — run fully offline by patching the heavy steps.

Asserts the constitutional guarantees that don't depend on the LLM output: raw audio
is never retained (Art. IV — stored uploads are removed on every terminal outcome),
any permanent failure ends as a clean `failed` status without crashing the worker, a
transient failure bubbles up for retry without being recorded as failed, and a
redelivered task is idempotent."""

from __future__ import annotations

import pytest

from app import pipeline, store
from app.models import Course, Lecture, LectureStatus, User


def _seed(tmp_path, *, audio_name="audio.mp3", pdf_name="slides.pdf"):
    owner = store.create_user(User(email="p@x.com"))
    course = store.create_course(Course(name="C", owner_id=owner.id))
    lec = store.create_lecture(
        Lecture(course_id=course.id, title="L", status=LectureStatus.processing)
    )
    # Place the uploads in shared storage exactly as ingest does (local backend here).
    audio_src = tmp_path / audio_name
    audio_src.write_bytes(b"FAKE-AUDIO-BYTES")
    pdf_src = tmp_path / pdf_name
    pdf_src.write_bytes(b"%PDF-1.4 fake")
    store.save_upload(lec.id, audio_name, str(audio_src))
    store.save_upload(lec.id, pdf_name, str(pdf_src))
    return course, lec, audio_name, pdf_name


def test_failure_marks_failed_and_deletes_uploads(monkeypatch, tmp_path):
    course, lec, audio_name, pdf_name = _seed(tmp_path)

    def boom(_path):
        raise RuntimeError("STT unavailable")

    monkeypatch.setattr(pipeline, "transcribe", boom)
    # Must not raise — a permanent error is swallowed and recorded.
    pipeline.run_pipeline(lec.id, course.id, audio_name, pdf_name)

    fresh = store.get_lecture(lec.id)
    assert fresh["status"] == "failed"
    assert "STT unavailable" in (fresh["progress"] or "")
    # Art. IV: no raw audio survives, even on failure.
    assert store.read_upload(lec.id, audio_name, str(tmp_path / "out")) is False


def test_empty_input_fails_gracefully_and_cleans_up(monkeypatch, tmp_path):
    course, lec, audio_name, pdf_name = _seed(tmp_path)
    monkeypatch.setattr(pipeline, "transcribe", lambda _p: [])
    monkeypatch.setattr(pipeline, "extract_slides", lambda _p: ([], []))
    monkeypatch.setattr(pipeline, "filter_images", lambda images, num_pages: [])
    monkeypatch.setattr(pipeline, "align", lambda sections, segments: [])

    pipeline.run_pipeline(lec.id, course.id, audio_name, pdf_name)

    assert store.get_lecture(lec.id)["status"] == "failed"  # "no content" → failed, no crash
    assert store.read_upload(lec.id, audio_name, str(tmp_path / "out")) is False


def test_transient_error_reraises_and_keeps_uploads(monkeypatch, tmp_path):
    """A transient error must propagate (so Celery retries) and NOT be recorded as
    failed, and the stored uploads must remain so the retry can re-read them."""
    course, lec, audio_name, pdf_name = _seed(tmp_path)

    def flaky(_path):
        raise ConnectionError("vector store unreachable")

    monkeypatch.setattr(pipeline, "transcribe", flaky)
    with pytest.raises(ConnectionError):
        pipeline.run_pipeline(lec.id, course.id, audio_name, pdf_name)

    assert store.get_lecture(lec.id)["status"] == "processing"   # not failed → will retry
    # uploads kept for the retry
    assert store.read_upload(lec.id, audio_name, str(tmp_path / "kept")) is True


def test_already_ready_is_noop(monkeypatch, tmp_path):
    """A redelivered task for an already-finished lecture must not reprocess."""
    course, lec, audio_name, pdf_name = _seed(tmp_path)
    store.update_lecture(lec.id, status=LectureStatus.ready, progress="Ready.")

    called = {"n": 0}
    monkeypatch.setattr(pipeline, "transcribe", lambda _p: called.__setitem__("n", 1))
    pipeline.run_pipeline(lec.id, course.id, audio_name, pdf_name)

    assert called["n"] == 0                                       # pipeline body never ran
    assert store.get_lecture(lec.id)["status"] == "ready"


def test_missing_inputs_fail_permanently(monkeypatch, tmp_path):
    """If the stored uploads are gone, the lecture fails (not retried forever)."""
    course = store.create_course(Course(name="C", owner_id=store.create_user(User(email="q@x.com")).id))
    lec = store.create_lecture(Lecture(course_id=course.id, title="L", status=LectureStatus.processing))
    # No save_upload → inputs missing.
    pipeline.run_pipeline(lec.id, course.id, "audio.mp3", "slides.pdf")
    assert store.get_lecture(lec.id)["status"] == "failed"
