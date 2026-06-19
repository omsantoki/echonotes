"""JSON-file registry backend (local dev).

A tiny JSON index of users/courses/lectures/diagrams/auth_tokens guarded by an
in-process lock. Single-process only — production uses the Postgres backend instead.

Feature 002 (Art. X): users + hashed auth tokens live here too, and course/lecture
reads/lists/deletes filter by `owner_id` when one is supplied (the owner filter is
enforced here, not only in the route). `owner_id=None` = internal/system path.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path

from app.config import get_settings
from app.models import (AuthToken, Course, DiagramAsset, Lecture, LectureStatus,
                        TokenKind, User)


class JsonRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()

    # --- file helpers ---
    def _path(self) -> Path:
        p = Path(get_settings().data_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p / "registry.json"

    def _load(self) -> dict:
        path = self._path()
        if not path.exists():
            return {"users": {}, "courses": {}, "lectures": {}, "diagrams": {}, "auth_tokens": {}}
        data = json.loads(path.read_text())
        for key in ("users", "courses", "lectures", "diagrams", "auth_tokens"):
            data.setdefault(key, {})
        return data

    def _save(self, data: dict) -> None:
        self._path().write_text(json.dumps(data, default=str, indent=2))

    # --- users (002) ---
    def create_user(self, user: User) -> User:
        with self._lock:
            data = self._load()
            data["users"][user.id] = user.model_dump(mode="json")
            self._save(data)
        return user

    def get_user(self, user_id: str) -> dict | None:
        return self._load()["users"].get(user_id)

    def get_user_by_email(self, email: str) -> dict | None:
        email = email.strip().lower()
        for u in self._load()["users"].values():
            if (u.get("email") or "").lower() == email:
                return u
        return None

    def get_user_by_google_sub(self, google_sub: str) -> dict | None:
        if not google_sub:
            return None
        for u in self._load()["users"].values():
            if u.get("google_sub") == google_sub:
                return u
        return None

    def update_user(self, user_id: str, changes: dict) -> None:
        with self._lock:
            data = self._load()
            u = data["users"].get(user_id)
            if not u:
                return
            u.update(changes)
            self._save(data)

    # --- auth tokens (002) — stored hashed, single-use, TTL'd ---
    def create_auth_token(self, token: AuthToken) -> AuthToken:
        with self._lock:
            data = self._load()
            data["auth_tokens"][token.id] = token.model_dump(mode="json")
            self._save(data)
        return token

    def find_auth_token(self, kind: TokenKind, *, user_id: str | None = None,
                        token_hash: str | None = None) -> dict | None:
        toks = [t for t in self._load()["auth_tokens"].values() if t["kind"] == kind.value]
        if token_hash is not None:
            toks = [t for t in toks if t["token_hash"] == token_hash]
        if user_id is not None:
            # the active code/token is the newest still-unused one for this user+kind
            toks = [t for t in toks if t["user_id"] == user_id and not t.get("used")]
        if not toks:
            return None
        toks.sort(key=lambda t: t.get("created_at", ""), reverse=True)
        return toks[0]

    def bump_auth_token(self, token_id: str, *, attempts: int | None = None,
                        used: bool | None = None) -> None:
        with self._lock:
            data = self._load()
            t = data["auth_tokens"].get(token_id)
            if not t:
                return
            if attempts is not None:
                t["attempts"] = attempts
            if used is not None:
                t["used"] = used
            self._save(data)

    def invalidate_auth_tokens(self, user_id: str, kind: TokenKind) -> None:
        with self._lock:
            data = self._load()
            for t in data["auth_tokens"].values():
                if t["user_id"] == user_id and t["kind"] == kind.value:
                    t["used"] = True
            self._save(data)

    # --- courses (owner-scoped) ---
    def create_course(self, course: Course) -> Course:
        with self._lock:
            data = self._load()
            data["courses"][course.id] = course.model_dump(mode="json")
            self._save(data)
        return course

    def list_courses(self, owner_id: str | None = None) -> list[dict]:
        data = self._load()
        courses = [
            c for c in data["courses"].values()
            if owner_id is None or c.get("owner_id") == owner_id
        ]
        for c in courses:
            c["lecture_count"] = sum(
                1 for lec in data["lectures"].values() if lec["course_id"] == c["id"]
            )
        return courses

    def get_course(self, course_id: str, owner_id: str | None = None) -> dict | None:
        course = self._load()["courses"].get(course_id)
        if course is None:
            return None
        if owner_id is not None and course.get("owner_id") != owner_id:
            return None  # not the owner → same as "not found" (no existence leak, Art. X)
        return course

    def delete_course_row(self, course_id: str, owner_id: str | None = None) -> bool:
        with self._lock:
            data = self._load()
            course = data["courses"].get(course_id)
            if course is None or (owner_id is not None and course.get("owner_id") != owner_id):
                return False
            del data["courses"][course_id]
            self._save(data)
        return True

    # --- lectures (owner-scoped via the parent course) ---
    def create_lecture(self, lecture: Lecture) -> Lecture:
        with self._lock:
            data = self._load()
            data["lectures"][lecture.id] = lecture.model_dump(mode="json")
            self._save(data)
        return lecture

    def _owns_lecture(self, data: dict, lec: dict, owner_id: str | None) -> bool:
        if owner_id is None:
            return True
        course = data["courses"].get(lec.get("course_id"))
        return bool(course) and course.get("owner_id") == owner_id

    def get_lecture(self, lecture_id: str, owner_id: str | None = None) -> dict | None:
        data = self._load()
        lec = data["lectures"].get(lecture_id)
        if lec is None or not self._owns_lecture(data, lec, owner_id):
            return None
        return lec

    def list_lectures(self, course_id: str) -> list[dict]:
        data = self._load()
        return [lec for lec in data["lectures"].values() if lec["course_id"] == course_id]

    def list_lecture_ids(self, course_id: str) -> list[str]:
        data = self._load()
        return [lid for lid, lec in data["lectures"].items() if lec.get("course_id") == course_id]

    def list_all_lectures(self) -> list[dict]:
        return list(self._load()["lectures"].values())

    def update_lecture(
        self, lecture_id: str, status: LectureStatus | None, progress: str | None
    ) -> None:
        with self._lock:
            data = self._load()
            lec = data["lectures"].get(lecture_id)
            if not lec:
                return
            if status is not None:
                lec["status"] = status.value
            if progress is not None:
                lec["progress"] = progress
            self._save(data)

    def set_lecture_links(self, lecture_id: str, links: dict) -> None:
        with self._lock:
            data = self._load()
            lec = data["lectures"].get(lecture_id)
            if not lec:
                return
            lec["links"] = links
            self._save(data)

    def delete_lecture_rows(self, lecture_id: str, owner_id: str | None = None) -> bool:
        """Remove the lecture record + its diagram rows. Returns False if absent or not owned."""
        with self._lock:
            data = self._load()
            lec = data["lectures"].get(lecture_id)
            if lec is None or not self._owns_lecture(data, lec, owner_id):
                return False
            data["diagrams"] = {
                aid: a for aid, a in data["diagrams"].items()
                if a.get("lecture_id") != lecture_id
            }
            del data["lectures"][lecture_id]
            self._save(data)
        return True

    # --- diagrams ---
    def create_diagram(self, asset: DiagramAsset) -> DiagramAsset:
        with self._lock:
            data = self._load()
            data["diagrams"][asset.id] = asset.model_dump(mode="json")
            self._save(data)
        return asset

    def get_diagram(self, asset_id: str) -> dict | None:
        return self._load()["diagrams"].get(asset_id)

    def list_diagrams(self, lecture_id: str) -> list[dict]:
        data = self._load()
        return [d for d in data["diagrams"].values() if d["lecture_id"] == lecture_id]

    def delete_diagrams_by_lecture(self, lecture_id: str) -> None:
        """Drop a lecture's diagram rows but keep the lecture itself (idempotent re-run)."""
        with self._lock:
            data = self._load()
            data["diagrams"] = {
                aid: a for aid, a in data["diagrams"].items()
                if a.get("lecture_id") != lecture_id
            }
            self._save(data)

    def list_all_diagrams(self) -> list[dict]:
        return list(self._load()["diagrams"].values())
