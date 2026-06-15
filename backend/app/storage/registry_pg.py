"""Managed Postgres registry backend (production).

Replaces registry.json for multi-instance deploys: every operation is a single
atomic statement (or FK cascade), so there is no read-modify-write race and no
in-process lock. Dicts returned here match the JSON backend's shape exactly
(ISO-string dates), so api/, render.py, web.py, auth/, and assemble_document see
no difference. Schema is created by scripts/init_db.py.

Feature 002 (Art. X): adds users + hashed auth tokens, and an `owner_id` on
courses. Owner-scoped reads/deletes filter in SQL (`WHERE owner_id = %s` / a JOIN
on the parent course), so isolation holds at the backend, not just the route.
`owner_id=None` is the internal/system path (no owner filter).
"""

from __future__ import annotations

import datetime as dt
from functools import lru_cache

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Json
from psycopg_pool import ConnectionPool

from app.config import get_settings
from app.models import (AuthToken, Course, DiagramAsset, Lecture, LectureStatus,
                        TokenKind, User)


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


def _user(row: dict | None) -> dict | None:
    if not row:
        return None
    return {
        "id": row["id"],
        "email": row["email"],
        "password_hash": row["password_hash"],
        "email_verified": row["email_verified"],
        "auth_provider": row["auth_provider"],
        "google_sub": row["google_sub"],
        "created_at": _iso(row["created_at"]),
    }


def _token(row: dict | None) -> dict | None:
    if not row:
        return None
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "kind": row["kind"],
        "token_hash": row["token_hash"],
        "expires_at": _iso(row["expires_at"]),
        "attempts": row["attempts"],
        "used": row["used"],
        "created_at": _iso(row["created_at"]),
    }


def _course(row: dict | None) -> dict | None:
    if not row:
        return None
    out = {"id": row["id"], "name": row["name"], "owner_id": row.get("owner_id"),
           "created_at": _iso(row["created_at"])}
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

    # --- users (002) ---
    def create_user(self, user: User) -> User:
        self._exec(
            "INSERT INTO users (id, email, password_hash, email_verified, auth_provider, "
            "google_sub, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (user.id, user.email, user.password_hash, user.email_verified,
             user.auth_provider.value, user.google_sub, user.created_at),
        )
        return user

    def get_user(self, user_id: str) -> dict | None:
        return _user(self._exec("SELECT * FROM users WHERE id = %s", (user_id,), fetch="one"))

    def get_user_by_email(self, email: str) -> dict | None:
        return _user(self._exec("SELECT * FROM users WHERE email = %s",
                                (email.strip().lower(),), fetch="one"))

    def get_user_by_google_sub(self, google_sub: str) -> dict | None:
        if not google_sub:
            return None
        return _user(self._exec("SELECT * FROM users WHERE google_sub = %s",
                                (google_sub,), fetch="one"))

    def update_user(self, user_id: str, changes: dict) -> None:
        if not changes:
            return
        cols = ", ".join(f"{k} = %s" for k in changes)
        self._exec(f"UPDATE users SET {cols} WHERE id = %s",
                   (*changes.values(), user_id))

    # --- auth tokens (002) ---
    def create_auth_token(self, token: AuthToken) -> AuthToken:
        self._exec(
            "INSERT INTO auth_tokens (id, user_id, kind, token_hash, expires_at, "
            "attempts, used, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (token.id, token.user_id, token.kind.value, token.token_hash,
             token.expires_at, token.attempts, token.used, token.created_at),
        )
        return token

    def find_auth_token(self, kind: TokenKind, *, user_id: str | None = None,
                        token_hash: str | None = None) -> dict | None:
        if token_hash is not None:
            row = self._exec(
                "SELECT * FROM auth_tokens WHERE kind = %s AND token_hash = %s "
                "ORDER BY created_at DESC LIMIT 1",
                (kind.value, token_hash), fetch="one")
        elif user_id is not None:
            row = self._exec(
                "SELECT * FROM auth_tokens WHERE kind = %s AND user_id = %s AND used = false "
                "ORDER BY created_at DESC LIMIT 1",
                (kind.value, user_id), fetch="one")
        else:
            return None
        return _token(row)

    def bump_auth_token(self, token_id: str, *, attempts: int | None = None,
                        used: bool | None = None) -> None:
        self._exec(
            "UPDATE auth_tokens SET attempts = COALESCE(%s, attempts), "
            "used = COALESCE(%s, used) WHERE id = %s",
            (attempts, used, token_id))

    def invalidate_auth_tokens(self, user_id: str, kind: TokenKind) -> None:
        self._exec("UPDATE auth_tokens SET used = true WHERE user_id = %s AND kind = %s",
                   (user_id, kind.value))

    # --- courses (owner-scoped) ---
    def create_course(self, course: Course) -> Course:
        self._exec(
            "INSERT INTO courses (id, name, owner_id, created_at) VALUES (%s, %s, %s, %s) "
            "ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, owner_id = EXCLUDED.owner_id",
            (course.id, course.name, course.owner_id, course.created_at),
        )
        return course

    def list_courses(self, owner_id: str | None = None) -> list[dict]:
        where = "WHERE c.owner_id = %s " if owner_id is not None else ""
        params = (owner_id,) if owner_id is not None else ()
        rows = self._exec(
            "SELECT c.id, c.name, c.owner_id, c.created_at, COUNT(l.id) AS lecture_count "
            "FROM courses c LEFT JOIN lectures l ON l.course_id = c.id "
            f"{where}"
            "GROUP BY c.id, c.name, c.owner_id, c.created_at ORDER BY c.created_at",
            params, fetch="all",
        )
        return [_course(r) for r in rows]

    def get_course(self, course_id: str, owner_id: str | None = None) -> dict | None:
        if owner_id is not None:
            row = self._exec("SELECT * FROM courses WHERE id = %s AND owner_id = %s",
                             (course_id, owner_id), fetch="one")
        else:
            row = self._exec("SELECT * FROM courses WHERE id = %s", (course_id,), fetch="one")
        return _course(row)

    def delete_course_row(self, course_id: str, owner_id: str | None = None) -> bool:
        if owner_id is not None:
            return bool(self._exec("DELETE FROM courses WHERE id = %s AND owner_id = %s",
                                   (course_id, owner_id)))
        return bool(self._exec("DELETE FROM courses WHERE id = %s", (course_id,)))

    # --- lectures (owner-scoped via the parent course) ---
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

    def get_lecture(self, lecture_id: str, owner_id: str | None = None) -> dict | None:
        if owner_id is not None:
            row = self._exec(
                "SELECT l.* FROM lectures l JOIN courses c ON c.id = l.course_id "
                "WHERE l.id = %s AND c.owner_id = %s",
                (lecture_id, owner_id), fetch="one")
        else:
            row = self._exec("SELECT * FROM lectures WHERE id = %s", (lecture_id,), fetch="one")
        return _lecture(row)

    def list_lectures(self, course_id: str) -> list[dict]:
        rows = self._exec(
            "SELECT * FROM lectures WHERE course_id = %s ORDER BY created_at", (course_id,), fetch="all"
        )
        return [_lecture(r) for r in rows]

    def list_lecture_ids(self, course_id: str) -> list[str]:
        rows = self._exec("SELECT id FROM lectures WHERE course_id = %s", (course_id,), fetch="all")
        return [r["id"] for r in rows]

    def list_all_lectures(self) -> list[dict]:
        return [_lecture(r) for r in self._exec("SELECT * FROM lectures", fetch="all")]

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

    def delete_lecture_rows(self, lecture_id: str, owner_id: str | None = None) -> bool:
        # diagrams rows are removed by the ON DELETE CASCADE foreign key.
        if owner_id is not None:
            return bool(self._exec(
                "DELETE FROM lectures l USING courses c "
                "WHERE l.id = %s AND l.course_id = c.id AND c.owner_id = %s",
                (lecture_id, owner_id)))
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
