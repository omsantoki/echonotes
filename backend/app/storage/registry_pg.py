"""Managed Postgres registry backend (production).

Replaces registry.json for multi-instance deploys: every operation is a single
atomic statement (or FK cascade), so there is no read-modify-write race and no
in-process lock. Dicts returned here match the JSON backend's shape exactly
(ISO-string dates), so api/, render.py, web.py and assemble_document see no
difference. Schema is created by scripts/init_db.py.
"""

from __future__ import annotations

import datetime as dt
from functools import lru_cache

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Json
from psycopg_pool import ConnectionPool

from app.config import get_settings
from app.models import Course, DiagramAsset, Lecture, LectureStatus


@lru_cache
def _pool() -> ConnectionPool:
    return ConnectionPool(
        get_settings().database_url,
        min_size=1,
        max_size=10,
        kwargs={"row_factory": dict_row},
        open=True,
    )


def _iso(value) -> str | None:
    return value.isoformat() if isinstance(value, (dt.date, dt.datetime)) else value


def _course(row: dict | None) -> dict | None:
    if not row:
        return None
    out = {"id": row["id"], "name": row["name"], "created_at": _iso(row["created_at"])}
    if "lecture_count" in row:
        out["lecture_count"] = row["lecture_count"]
    return out


def _lecture(row: dict | None) -> dict | None:
    if not row:
        return None
    return {
        "id": row["id"],
        "course_id": row["course_id"],
        "title": row["title"],
        "date": _iso(row["date"]),
        "status": row["status"],
        "progress": row["progress"],
        "links": row["links"] or {},
        "created_at": _iso(row["created_at"]),
    }


def _diagram(row: dict | None) -> dict | None:
    if not row:
        return None
    return {
        "id": row["id"],
        "lecture_id": row["lecture_id"],
        "image_ref": row["image_ref"],
        "section_topic": row["section_topic"],
        "description": row["description"],
    }


class PostgresRegistry:
    def _exec(self, sql: str, params: tuple = (), fetch: str | None = None):
        with _pool().connection() as conn, conn.cursor() as cur:
            cur.execute(sql, params)
            if fetch == "one":
                return cur.fetchone()
            if fetch == "all":
                return cur.fetchall()
            return cur.rowcount

    # --- courses ---
    def create_course(self, course: Course) -> Course:
        self._exec(
            "INSERT INTO courses (id, name, created_at) VALUES (%s, %s, %s) "
            "ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name",
            (course.id, course.name, course.created_at),
        )
        return course

    def list_courses(self) -> list[dict]:
        rows = self._exec(
            "SELECT c.id, c.name, c.created_at, COUNT(l.id) AS lecture_count "
            "FROM courses c LEFT JOIN lectures l ON l.course_id = c.id "
            "GROUP BY c.id, c.name, c.created_at ORDER BY c.created_at",
            fetch="all",
        )
        return [_course(r) for r in rows]

    def get_course(self, course_id: str) -> dict | None:
        return _course(self._exec("SELECT * FROM courses WHERE id = %s", (course_id,), fetch="one"))

    def delete_course_row(self, course_id: str) -> bool:
        return bool(self._exec("DELETE FROM courses WHERE id = %s", (course_id,)))

    # --- lectures ---
    def create_lecture(self, lecture: Lecture) -> Lecture:
        self._exec(
            "INSERT INTO lectures (id, course_id, title, date, status, progress, created_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s) "
            "ON CONFLICT (id) DO UPDATE SET course_id = EXCLUDED.course_id, "
            "title = EXCLUDED.title, date = EXCLUDED.date, status = EXCLUDED.status, "
            "progress = EXCLUDED.progress",
            (lecture.id, lecture.course_id, lecture.title, lecture.date,
             lecture.status.value, lecture.progress, lecture.created_at),
        )
        return lecture

    def get_lecture(self, lecture_id: str) -> dict | None:
        return _lecture(self._exec("SELECT * FROM lectures WHERE id = %s", (lecture_id,), fetch="one"))

    def list_lectures(self, course_id: str) -> list[dict]:
        rows = self._exec(
            "SELECT * FROM lectures WHERE course_id = %s ORDER BY created_at", (course_id,), fetch="all"
        )
        return [_lecture(r) for r in rows]

    def list_lecture_ids(self, course_id: str) -> list[str]:
        rows = self._exec("SELECT id FROM lectures WHERE course_id = %s", (course_id,), fetch="all")
        return [r["id"] for r in rows]

    def update_lecture(
        self, lecture_id: str, status: LectureStatus | None, progress: str | None
    ) -> None:
        self._exec(
            "UPDATE lectures SET status = COALESCE(%s, status), "
            "progress = COALESCE(%s, progress) WHERE id = %s",
            (status.value if status else None, progress, lecture_id),
        )

    def set_lecture_links(self, lecture_id: str, links: dict) -> None:
        self._exec("UPDATE lectures SET links = %s WHERE id = %s", (Json(links), lecture_id))

    def delete_lecture_rows(self, lecture_id: str) -> bool:
        # diagrams rows are removed by the ON DELETE CASCADE foreign key.
        return bool(self._exec("DELETE FROM lectures WHERE id = %s", (lecture_id,)))

    # --- diagrams ---
    def create_diagram(self, asset: DiagramAsset) -> DiagramAsset:
        self._exec(
            "INSERT INTO diagrams (id, lecture_id, image_ref, section_topic, description) "
            "VALUES (%s, %s, %s, %s, %s) "
            "ON CONFLICT (id) DO UPDATE SET image_ref = EXCLUDED.image_ref, "
            "section_topic = EXCLUDED.section_topic, description = EXCLUDED.description",
            (asset.id, asset.lecture_id, asset.image_ref, asset.section_topic, asset.description),
        )
        return asset

    def get_diagram(self, asset_id: str) -> dict | None:
        return _diagram(self._exec("SELECT * FROM diagrams WHERE id = %s", (asset_id,), fetch="one"))

    def list_diagrams(self, lecture_id: str) -> list[dict]:
        rows = self._exec("SELECT * FROM diagrams WHERE lecture_id = %s", (lecture_id,), fetch="all")
        return [_diagram(r) for r in rows]

    def list_all_diagrams(self) -> list[dict]:
        return [_diagram(r) for r in self._exec("SELECT * FROM diagrams", fetch="all")]
