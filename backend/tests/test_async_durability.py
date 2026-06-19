"""Tests for the production-hardening of the async pipeline:

- shared upload handoff (the worker reads what the web service wrote),
- idempotent re-run reset (no duplicate chunks/diagrams),
- task on_failure cleanup (no audio survives retry exhaustion — Art. IV),
- Celery-aware startup recovery (a web restart must not fail worker-owned lectures).

Hermetic: local object/registry/vector backends, no broker, no real Redis.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app import store, tasks
from app.config import get_settings
from app.models import Course, Lecture, LectureStatus, NoteChunk, SourceType, User


def _course(email="d@x.com"):
    owner = store.create_user(User(email=email))
    return store.create_course(Course(name="C", owner_id=owner.id))


# --------------------------------------------------------------------------- #
# Shared upload handoff
# --------------------------------------------------------------------------- #

def test_upload_roundtrip_through_store(tmp_path):
    src = tmp_path / "audio.mp3"
    src.write_bytes(b"hello-bytes")
    store.save_upload("lec1", "audio.mp3", str(src))

    dest = tmp_path / "fetched.mp3"
    assert store.read_upload("lec1", "audio.mp3", str(dest)) is True
    assert dest.read_bytes() == b"hello-bytes"

    store.delete_uploads("lec1")
    assert store.read_upload("lec1", "audio.mp3", str(tmp_path / "x")) is False


# --------------------------------------------------------------------------- #
# Idempotent re-run reset
# --------------------------------------------------------------------------- #

def test_reset_clears_chunks_and_diagrams_but_keeps_lecture(tmp_path):
    course = _course()
    lec = store.create_lecture(Lecture(course_id=course.id, title="L",
                                       status=LectureStatus.processing))
    store.add_chunks([NoteChunk(lecture_id=lec.id, course_id=course.id, topic="T",
                                order=0, text="a point", source_type=SourceType.slides,
                                reason="r", confidence=1.0, embedding=[0.1, 0.2, 0.3])])
    img = tmp_path / "d.png"
    img.write_bytes(b"img")
    asset_ref = store.save_diagram_image(lec.id, "asset1", "png", b"img")
    from app.models import DiagramAsset
    store.create_diagram(DiagramAsset(id="asset1", lecture_id=lec.id,
                                      image_ref=asset_ref, section_topic="T"))
    assert store.list_chunks(lec.id) and store.list_diagrams(lec.id)

    store.reset_lecture_artifacts(lec.id)

    assert store.list_chunks(lec.id) == []
    assert store.list_diagrams(lec.id) == []
    assert store.get_lecture(lec.id) is not None          # lecture row survives


# --------------------------------------------------------------------------- #
# Task on_failure: record + clean uploads when retries are exhausted (Art. IV)
# --------------------------------------------------------------------------- #

def test_task_on_failure_marks_failed_and_deletes_uploads(tmp_path):
    course = _course("f@x.com")
    lec = store.create_lecture(Lecture(course_id=course.id, title="L",
                                       status=LectureStatus.processing))
    src = tmp_path / "audio.mp3"
    src.write_bytes(b"bytes")
    store.save_upload(lec.id, "audio.mp3", str(src))

    tasks.process_lecture.on_failure(
        ConnectionError("still down"), "task-id",
        (lec.id, course.id, "audio.mp3", "slides.pdf"), {}, None,
    )

    assert store.get_lecture(lec.id)["status"] == "failed"
    assert store.read_upload(lec.id, "audio.mp3", str(tmp_path / "x")) is False


# --------------------------------------------------------------------------- #
# Celery-aware startup recovery
# --------------------------------------------------------------------------- #

def test_lifespan_recovers_orphans_in_inline_mode():
    # Default test config: no REDIS_URL → inline → a web restart fails in-flight work.
    course = _course("inline@x.com")
    lec = store.create_lecture(Lecture(course_id=course.id, title="L",
                                       status=LectureStatus.processing))
    from app.main import app
    with TestClient(app):
        pass
    assert store.get_lecture(lec.id)["status"] == "failed"


def test_lifespan_leaves_orphans_in_celery_mode(monkeypatch):
    # With a broker, the worker survives a web restart — a deploy must NOT fail
    # lectures the worker is still processing.
    monkeypatch.setenv("REDIS_URL", "redis://unused:6379/0")
    monkeypatch.setenv("TASK_ALWAYS_EAGER", "false")
    get_settings.cache_clear()

    course = _course("celery@x.com")
    lec = store.create_lecture(Lecture(course_id=course.id, title="L",
                                       status=LectureStatus.processing))
    from app.main import app
    with TestClient(app):
        pass
    assert store.get_lecture(lec.id)["status"] == "processing"   # untouched
