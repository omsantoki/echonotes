"""Create the Postgres schema for the EchoNotes registry (idempotent).

Run once against the managed database before first use:
    DATABASE_URL=postgresql://… python scripts/init_db.py
"""

from __future__ import annotations

import pathlib
import sys

ROOT = str(pathlib.Path(__file__).resolve().parent.parent)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import psycopg  # noqa: E402

from app.config import get_settings  # noqa: E402

DDL = """
CREATE TABLE IF NOT EXISTS courses (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS lectures (
    id          TEXT PRIMARY KEY,
    course_id   TEXT NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    title       TEXT NOT NULL,
    date        DATE,
    status      TEXT NOT NULL DEFAULT 'uploaded',
    progress    TEXT NOT NULL DEFAULT '',
    links       JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS lectures_course_id_idx ON lectures(course_id);

CREATE TABLE IF NOT EXISTS diagrams (
    id            TEXT PRIMARY KEY,
    lecture_id    TEXT NOT NULL REFERENCES lectures(id) ON DELETE CASCADE,
    image_ref     TEXT NOT NULL,
    section_topic TEXT NOT NULL,
    description   TEXT
);
CREATE INDEX IF NOT EXISTS diagrams_lecture_id_idx ON diagrams(lecture_id);
"""


def main() -> int:
    url = get_settings().database_url
    if not url:
        print("DATABASE_URL is not set — nothing to do.")
        return 1
    with psycopg.connect(url) as conn:
        conn.execute(DDL)
        conn.commit()
    print("Schema ready (courses, lectures, diagrams).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
