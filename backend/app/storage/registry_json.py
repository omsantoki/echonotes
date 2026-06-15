"""JSON-file registry backend (local dev).

A tiny JSON index of courses/lectures/diagrams guarded by an in-process lock.
Single-process only — production uses the Postgres backend instead.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path

from app.config import get_settings
from app.models import Course, DiagramAsset, Lecture, LectureStatus


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
            return {"courses": {}, "lectures": {}, "diagrams": {}}
        data = json.loads(path.read_text())
        data.setdefault("courses", {})
        data.setdefault("lectures", {})
        data.setdefault("diagrams", {})
        return data

    def _save(self, data: dict) -> None:
        self._path().write_text(json.dumps(data, default=str, indent=2))

    # --- courses ---
    def create_course(self, course: Course) -> Course:
        with self._lock:
            data = self._load()
            data["courses"][course.id] = course.model_dump(mode="json")
            self._save(data)
        return course

    def list_courses(self) -> list[dict]:
        data = self._load()
        courses = list(data["courses"].values())
        for c in courses:
            c["lecture_count"] = sum(
                1 for lec in data["lectures"].values() if lec["course_id"] == c["id"]
            )
        return courses

    def get_course(self, course_id: str) -> dict | None:
        return self._load()["courses"].get(course_id)

    def delete_course_row(self, course_id: str) -> bool:
        with self._lock:
            data = self._load()
            existed = data["courses"].pop(course_id, None) is not None
            if existed:
                self._save(data)
        return existed

    # --- lectures ---
    def create_lecture(self, lecture: Lecture) -> Lecture:
        with self._lock:
            data = self._load()
            data["lectures"][lecture.id] = lecture.model_dump(mode="json")
            self._save(data)
        return lecture

    def get_lecture(self, lecture_id: str) -> dict | None:
        return self._load()["lectures"].get(lecture_id)

    def list_lectures(self, course_id: str) -> list[dict]:
        data = self._load()
        return [lec for lec in data["lectures"].values() if lec["course_id"] == course_id]

    def list_lecture_ids(self, course_id: str) -> list[str]:
        data = self._load()
        return [lid for lid, lec in data["lectures"].items() if lec.get("course_id") == course_id]

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

    def delete_lecture_rows(self, lecture_id: str) -> bool:
        """Remove the lecture record + its diagram rows. Returns False if absent."""
        with self._lock:
            data = self._load()
            if lecture_id not in data["lectures"]:
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

    def list_all_diagrams(self) -> list[dict]:
        return list(self._load()["diagrams"].values())
