"""Document assembly + export read-path tests (owner-scoped), exercising the
vector store (local Chroma), assemble_document, render, and the export endpoint."""

from __future__ import annotations

from app import store
from app.models import Course, Lecture, LectureStatus, NoteChunk, SourceType
from tests.conftest import auth_headers


def _ready_lecture_with_notes(owner_id: str):
    course = store.create_course(Course(name="Bio", owner_id=owner_id))
    lec = store.create_lecture(
        Lecture(course_id=course.id, title="L01", status=LectureStatus.ready, progress="Ready.")
    )
    store.add_chunks([
        NoteChunk(lecture_id=lec.id, course_id=course.id, topic="Intro", order=0,
                  text="Photosynthesis overview from the deck.", source_type=SourceType.slides,
                  reason="From slides section 'Intro'.", embedding=[0.1, 0.2, 0.3]),
        NoteChunk(lecture_id=lec.id, course_id=course.id, topic="Intro", order=1,
                  text="Water is split into oxygen — said aloud.", source_type=SourceType.spoken,
                  reason="★ Spoken-only (not on the slides) — matched by similarity.",
                  embedding=[0.2, 0.1, 0.4]),
    ])
    return course, lec


def test_get_ready_lecture_returns_labeled_document(client, register):
    me = register("d@x.com")
    _, lec = _ready_lecture_with_notes(me["user"]["id"])

    r = client.get(f"/api/lectures/{lec.id}", headers=auth_headers(me["session_token"]))
    assert r.status_code == 200
    topics = r.json()["document"]["topics"]
    assert topics[0]["topic"] == "Intro"
    segs = topics[0]["segments"]
    assert {s["source_type"] for s in segs} == {"slides", "spoken"}
    assert all(s["reason"] for s in segs)            # every block carries a reason (Art. II)
    assert any(s["spoken_only"] for s in segs)       # the ★ spoken-only flag (Art. III)


def test_export_markdown_html_and_bad_format(client, register):
    me = register("e@x.com")
    _, lec = _ready_lecture_with_notes(me["user"]["id"])
    h = auth_headers(me["session_token"])

    md = client.get(f"/api/lectures/{lec.id}/export?format=md", headers=h)
    assert md.status_code == 200 and b"Photosynthesis" in md.content

    html = client.get(f"/api/lectures/{lec.id}/export?format=html", headers=h)
    assert html.status_code == 200 and b"<" in html.content

    bad = client.get(f"/api/lectures/{lec.id}/export?format=pdf", headers=h)
    assert bad.status_code == 400


def test_export_is_owner_scoped(client, register):
    owner = register("owner@x.com")
    other = register("other@x.com")
    _, lec = _ready_lecture_with_notes(owner["user"]["id"])
    r = client.get(f"/api/lectures/{lec.id}/export?format=md", headers=auth_headers(other["session_token"]))
    assert r.status_code == 404
