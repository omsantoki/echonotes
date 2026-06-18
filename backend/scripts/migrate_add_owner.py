"""Migrate pre-002 "common" courses to a bootstrap owner (feature 002, Art. X).

Before feature 002 every course was global with no owner. This one-shot, idempotent
script ensures a bootstrap admin user exists (BOOTSTRAP_ADMIN_EMAIL) and assigns every
ownerless course to it — so legacy data is never dropped, just owned. Run AFTER
`scripts/init_db.py` on Postgres deploys; on local dev (registry.json) just run this.

    # from backend/
    python scripts/migrate_add_owner.py

The bootstrap admin starts with no usable password; run forgot-password against
BOOTSTRAP_ADMIN_EMAIL (reset link prints to the server log in dev) to claim the
migrated library as a normal account.
"""

from __future__ import annotations

import pathlib
import sys

ROOT = str(pathlib.Path(__file__).resolve().parent.parent)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import store                       # noqa: E402
from app.auth.service import ensure_bootstrap_admin  # noqa: E402


def main() -> int:
    admin = ensure_bootstrap_admin()
    # System path (owner_id=None) returns ALL courses regardless of owner.
    all_courses = store.list_courses(owner_id=None)
    legacy = [c for c in all_courses if not c.get("owner_id")]

    if not legacy:
        print(f"Nothing to migrate — every course already has an owner "
              f"(bootstrap admin: {admin['email']}).")
        return 0

    from app.models import Course
    for c in legacy:
        # create_course upserts by id, so re-saving with owner_id set is an in-place update;
        # preserve the original created_at (the JSON backend rewrites the whole row).
        store.create_course(Course(id=c["id"], name=c["name"], owner_id=admin["id"],
                                   created_at=c["created_at"]))
    print(f"Assigned {len(legacy)} legacy course(s) to bootstrap admin {admin['email']}.")
    print("Claim it: run forgot-password for that email and use the reset link.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
