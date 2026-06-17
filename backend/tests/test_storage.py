"""Storage-layer tests (feature 002): users, hashed auth tokens, and the owner
scoping + cascade enforced by the JSON registry behind `store`. The owner filter
must hold at the STORAGE layer, not just the route (Constitution Art. X)."""

from __future__ import annotations

import datetime as dt
import hashlib

from app import store
from app.models import AuthToken, Course, Lecture, LectureStatus, TokenKind, User


def _user(email: str = "a@x.com") -> User:
    return store.create_user(User(email=email.lower()))


def _future() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1)


# --- users ---------------------------------------------------------------- #

def test_user_crud_and_case_insensitive_email_lookup():
    u = _user("mixed@case.com")
    assert store.get_user(u.id)["id"] == u.id
    assert store.get_user_by_email("MIXED@CASE.COM")["id"] == u.id  # query normalized
    assert store.get_user_by_email("nobody@x.com") is None


def test_update_user_applies_changes():
    u = _user()
    store.update_user(u.id, {"password_hash": "h", "email_verified": True})
    fresh = store.get_user(u.id)
    assert fresh["password_hash"] == "h" and fresh["email_verified"] is True


def test_get_user_by_google_sub():
    u = store.create_user(User(email="g@x.com", google_sub="sub-1"))
    assert store.get_user_by_google_sub("sub-1")["id"] == u.id
    assert store.get_user_by_google_sub("nope") is None


# --- auth tokens (hashed, single-use, attempt-limited) -------------------- #

def test_auth_token_single_use_and_lookup_modes():
    u = _user()
    h = hashlib.sha256(b"secret").hexdigest()
    store.create_auth_token(AuthToken(user_id=u.id, kind=TokenKind.reset, token_hash=h, expires_at=_future()))

    by_hash = store.find_auth_token(TokenKind.reset, token_hash=h)
    assert by_hash and by_hash["used"] is False
    by_user = store.find_auth_token(TokenKind.reset, user_id=u.id)
    assert by_user["id"] == by_hash["id"]

    store.bump_auth_token(by_hash["id"], used=True)
    # found-by-hash still returns it (so the service can reject a consumed token)...
    assert store.find_auth_token(TokenKind.reset, token_hash=h)["used"] is True
    # ...but the by-user lookup only returns UNUSED tokens.
    assert store.find_auth_token(TokenKind.reset, user_id=u.id) is None


def test_issue_new_token_invalidates_prior_ones():
    u = _user()
    store.create_auth_token(AuthToken(user_id=u.id, kind=TokenKind.otp,
                                      token_hash="old", expires_at=_future()))
    store.invalidate_auth_tokens(u.id, TokenKind.otp)
    assert store.find_auth_token(TokenKind.otp, user_id=u.id) is None


def test_bump_attempts():
    u = _user()
    store.create_auth_token(AuthToken(user_id=u.id, kind=TokenKind.otp, token_hash="h", expires_at=_future()))
    tok = store.find_auth_token(TokenKind.otp, user_id=u.id)
    store.bump_auth_token(tok["id"], attempts=3)
    assert store.find_auth_token(TokenKind.otp, user_id=u.id)["attempts"] == 3


# --- course / lecture owner scoping + cascade ----------------------------- #

def test_course_and_lecture_owner_scoping_and_cascade():
    a, b = _user("a@x.com"), _user("b@x.com")
    ca = store.create_course(Course(name="A-course", owner_id=a.id))

    # listing + get are owner-scoped (Art. X)
    assert [c["id"] for c in store.list_courses(owner_id=a.id)] == [ca.id]
    assert store.list_courses(owner_id=b.id) == []
    assert store.get_course(ca.id, owner_id=a.id)["id"] == ca.id
    assert store.get_course(ca.id, owner_id=b.id) is None

    lec = store.create_lecture(Lecture(course_id=ca.id, title="L", status=LectureStatus.ready))
    assert store.get_lecture(lec.id, owner_id=a.id)["id"] == lec.id
    assert store.get_lecture(lec.id, owner_id=b.id) is None
    assert lec.id in [l["id"] for l in store.list_all_lectures()]  # system path sees all

    # non-owner cannot delete either
    assert store.delete_course(ca.id, owner_id=b.id) is False
    assert store.delete_lecture(lec.id, owner_id=b.id) is False
    assert store.get_lecture(lec.id) is not None  # still there

    # owner deletes course → its lectures cascade away
    assert store.delete_course(ca.id, owner_id=a.id) is True
    assert store.get_course(ca.id) is None
    assert store.get_lecture(lec.id) is None


def test_diagram_rows():
    from app.models import DiagramAsset
    a = _user()
    ca = store.create_course(Course(name="C", owner_id=a.id))
    lec = store.create_lecture(Lecture(course_id=ca.id, title="L"))
    d = store.create_diagram(DiagramAsset(lecture_id=lec.id, image_ref="/assets/x.png",
                                          section_topic="Intro"))
    assert store.get_diagram(d.id)["id"] == d.id
    assert [x["id"] for x in store.list_diagrams(lec.id)] == [d.id]
    assert d.id in [x["id"] for x in store.list_all_diagrams()]
