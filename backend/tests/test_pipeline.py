"""Pipeline orchestration tests — run fully offline by patching the heavy steps.

Asserts the constitutional guarantees that don't depend on the LLM output: raw
audio + temp workspace are always deleted (Art. IV), and any failure ends as a
clean `failed` status without crashing the worker."""

from __future__ import annotations

from app import pipeline, store
from app.models import Course, Lecture, LectureStatus, User


def _seed(tmp_path):
    owner = store.create_user(User(email="p@x.com"))
    course = store.create_course(Course(name="C", owner_id=owner.id))
    lec = store.create_lecture(
        Lecture(course_id=course.id, title="L", status=LectureStatus.processing)
    )
    work = tmp_path / "work"
    work.mkdir()
    audio = work / "audio.mp3"
    audio.write_bytes(b"FAKE-AUDIO-BYTES")
    pdf = work / "slides.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    return course, lec, work, audio, pdf


def test_failure_marks_failed_and_deletes_audio(monkeypatch, tmp_path):
    course, lec, work, audio, pdf = _seed(tmp_path)

    def boom(_path):
        raise RuntimeError("STT unavailable")

    monkeypatch.setattr(pipeline, "transcribe", boom)
    # Must not raise — the worker swallows the error and records it.
    pipeline.run_pipeline(lec.id, course.id, str(audio), str(pdf), str(work))

    fresh = store.get_lecture(lec.id)
    assert fresh["status"] == "failed"
    assert "STT unavailable" in (fresh["progress"] or "")
    assert not audio.exists()  # Art. IV: no raw audio survives, even on failure
    assert not work.exists()   # the whole temp workspace is removed


def test_empty_input_fails_gracefully_and_cleans_up(monkeypatch, tmp_path):
    course, lec, work, audio, pdf = _seed(tmp_path)
    monkeypatch.setattr(pipeline, "transcribe", lambda _p: [])
    monkeypatch.setattr(pipeline, "extract_slides", lambda _p: ([], []))
    monkeypatch.setattr(pipeline, "filter_images", lambda images, num_pages: [])
    monkeypatch.setattr(pipeline, "align", lambda sections, segments: [])

    pipeline.run_pipeline(lec.id, course.id, str(audio), str(pdf), str(work))

    assert store.get_lecture(lec.id)["status"] == "failed"  # "no content" → failed, no crash
    assert not audio.exists()
    assert not work.exists()
