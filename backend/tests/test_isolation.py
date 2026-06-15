"""Per-user data isolation tests (feature 002, task T125, Constitution Art. X).

User A's courses/lectures/search are invisible and untouchable to user B: every
cross-tenant access returns 404 (never 403 — existence is not leaked), and an
unauthenticated request returns 401. New courses are owned by their creator.
"""

from __future__ import annotations

from tests.conftest import auth_headers


def _make_course(client, token, name):
    r = client.post("/api/courses", json={"name": name}, headers=auth_headers(token))
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _seed_ready_lecture(course_id, title="Owned lecture"):
    """Insert a ready lecture under a course directly (no heavy pipeline needed)."""
    from app import store
    from app.models import Lecture, LectureStatus

    lec = Lecture(course_id=course_id, title=title, status=LectureStatus.ready, progress="Ready.")
    store.create_lecture(lec)
    return lec.id


# --------------------------------------------------------------------------- #
# Auth required (401 before any ownership check)
# --------------------------------------------------------------------------- #

def test_data_routes_require_session(client):
    assert client.get("/api/courses").status_code == 401
    assert client.post("/api/courses", json={"name": "x"}).status_code == 401
    assert client.get("/api/courses/nope").status_code == 401
    assert client.get("/api/lectures/nope").status_code == 401
    assert client.delete("/api/courses/nope").status_code == 401


# --------------------------------------------------------------------------- #
# Listing + ownership
# --------------------------------------------------------------------------- #

def test_new_course_owned_by_creator_and_listing_is_scoped(client, register):
    a = register("a@example.com")["session_token"]
    b = register("b@example.com")["session_token"]

    a_course = _make_course(client, a, "A — Thermodynamics")

    # A sees their course; B sees nothing of A's
    a_list = client.get("/api/courses", headers=auth_headers(a)).json()
    b_list = client.get("/api/courses", headers=auth_headers(b)).json()
    assert [c["id"] for c in a_list] == [a_course]
    assert b_list == []

    # A can fetch their own course
    assert client.get(f"/api/courses/{a_course}", headers=auth_headers(a)).status_code == 200


def test_cross_tenant_course_access_is_404(client, register):
    a = register("a@example.com")["session_token"]
    b = register("b@example.com")["session_token"]
    a_course = _make_course(client, a, "A — Private")

    # B probing A's course → 404 (same as a truly-missing course), never 403
    assert client.get(f"/api/courses/{a_course}", headers=auth_headers(b)).status_code == 404
    assert client.get(f"/api/courses/{a_course}/search?q=x", headers=auth_headers(b)).status_code == 404
    assert client.delete(f"/api/courses/{a_course}", headers=auth_headers(b)).status_code == 404
    missing = client.get("/api/courses/does-not-exist", headers=auth_headers(b))
    real_but_foreign = client.get(f"/api/courses/{a_course}", headers=auth_headers(b))
    # Same status + error code → a foreign course is indistinguishable from a missing one
    # (the message only echoes the id the caller already supplied; nothing internal leaks).
    assert missing.status_code == real_but_foreign.status_code == 404
    assert missing.json()["error"]["code"] == real_but_foreign.json()["error"]["code"] == "course_not_found"

    # …and A's course is untouched after B's failed delete
    assert client.get(f"/api/courses/{a_course}", headers=auth_headers(a)).status_code == 200


def test_cross_tenant_lecture_access_is_404(client, register):
    a = register("a@example.com")["session_token"]
    b = register("b@example.com")["session_token"]
    a_course = _make_course(client, a, "A — With lecture")
    lec_id = _seed_ready_lecture(a_course)

    # A owns it
    assert client.get(f"/api/lectures/{lec_id}", headers=auth_headers(a)).status_code == 200
    # B cannot read / export / delete it
    assert client.get(f"/api/lectures/{lec_id}", headers=auth_headers(b)).status_code == 404
    assert client.get(f"/api/lectures/{lec_id}/export", headers=auth_headers(b)).status_code == 404
    assert client.delete(f"/api/lectures/{lec_id}", headers=auth_headers(b)).status_code == 404
    # still there for A
    assert client.get(f"/api/lectures/{lec_id}", headers=auth_headers(a)).status_code == 200


def test_cannot_upload_to_someone_elses_course(client, register):
    a = register("a@example.com")["session_token"]
    b = register("b@example.com")["session_token"]
    a_course = _make_course(client, a, "A — Upload target")

    files = {"audio": ("a.mp3", b"fake-audio", "audio/mpeg"),
             "slides": ("s.pdf", b"%PDF-1.4 fake", "application/pdf")}
    r = client.post("/api/lectures", data={"course_id": a_course, "title": "Sneaky"},
                    files=files, headers=auth_headers(b))
    assert r.status_code == 404 and r.json()["error"]["code"] == "course_not_found"


def test_owner_search_is_allowed(client, register, monkeypatch):
    # stub the vector-backed search so the test stays offline (no embeddings/Chroma)
    monkeypatch.setattr("app.retrieve.search", lambda course_id, q, n=None: [])
    a = register("a@example.com")["session_token"]
    a_course = _make_course(client, a, "A — Searchable")
    r = client.get(f"/api/courses/{a_course}/search?q=entropy", headers=auth_headers(a))
    assert r.status_code == 200 and r.json() == {"query": "entropy", "results": []}
