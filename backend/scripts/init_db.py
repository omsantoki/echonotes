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
-- Users + hashed auth tokens (feature 002, Constitution Art. X). Secrets are
-- never stored in plaintext: password_hash is a bcrypt hash; auth_tokens hold
-- only the sha256 of the OTP / reset token.
CREATE TABLE IF NOT EXISTS users (
    id             TEXT PRIMARY KEY,
    email          TEXT NOT NULL UNIQUE,
    password_hash  TEXT,
    email_verified BOOLEAN NOT NULL DEFAULT false,
    auth_provider  TEXT NOT NULL DEFAULT 'local',
    google_sub     TEXT UNIQUE,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS users_email_idx ON users(lower(email));

CREATE TABLE IF NOT EXISTS auth_tokens (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind        TEXT NOT NULL,             -- otp | set_password | reset
    token_hash  TEXT NOT NULL,             -- sha256 of the secret; never plaintext
    expires_at  TIMESTAMPTZ NOT NULL,
    attempts    INTEGER NOT NULL DEFAULT 0,
    used        BOOLEAN NOT NULL DEFAULT false,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS auth_tokens_user_kind_idx ON auth_tokens(user_id, kind);
CREATE INDEX IF NOT EXISTS auth_tokens_hash_idx ON auth_tokens(kind, token_hash);

CREATE TABLE IF NOT EXISTS courses (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- owner_id added separately (idempotent) so an existing deploy upgrades in place
-- without dropping data; the migrate_add_owner.py script then backfills legacy rows.
ALTER TABLE courses ADD COLUMN IF NOT EXISTS owner_id TEXT REFERENCES users(id);
CREATE INDEX IF NOT EXISTS courses_owner_id_idx ON courses(owner_id);

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
    print("Schema ready (users, auth_tokens, courses[+owner_id], lectures, diagrams).")
    print("Next: run `python scripts/migrate_add_owner.py` to assign legacy courses to the bootstrap admin.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
