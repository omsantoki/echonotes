"""Course endpoints (contracts/api.md; backs the T021 library).

Feature 002 (Art. X): every route requires an authenticated owner and is scoped to
them. Listing returns only the caller's courses; fetching/searching/deleting a course
the caller does not own returns 404 (never 403 — existence is not leaked). The owner
filter itself lives in the storage layer; here we just pass `user["id"]`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from app import retrieve, store
from app.auth.deps import get_current_user
from app.models import Course

router = APIRouter(prefix="/api/courses", tags=["courses"])


class CourseIn(BaseModel):
    name: str


def _require_owned_course(course_id: str, user: dict) -> dict:
    course = store.get_course(course_id, owner_id=user["id"])
    if not course:
        raise HTTPException(404, detail={"code": "course_not_found",
                                         "message": f"No course {course_id}."})
    return course


@router.post("", status_code=201)
def create_course(body: CourseIn, user: dict = Depends(get_current_user)):
    course = store.create_course(Course(name=body.name, owner_id=user["id"]))
    return {"id": course.id, "name": course.name,
            "created_at": course.created_at.isoformat()}


@router.get("")
def list_courses(user: dict = Depends(get_current_user)):
    return [{"id": c["id"], "name": c["name"], "lecture_count": c.get("lecture_count", 0)}
            for c in store.list_courses(owner_id=user["id"])]


@router.get("/{course_id}")
def get_course(course_id: str, user: dict = Depends(get_current_user)):
    course = _require_owned_course(course_id, user)
    lectures = [{"id": l["id"], "title": l["title"], "date": l.get("date"),
                 "status": l["status"]}
                for l in store.list_lectures(course_id)]
    return {"id": course["id"], "name": course["name"], "lectures": lectures}


@router.get("/{course_id}/search")
def search_course(course_id: str, q: str = "", user: dict = Depends(get_current_user)):
    """Cross-lecture search within a course (Strong, T031/FR-10), owner-scoped."""
    _require_owned_course(course_id, user)
    return {"query": q, "results": retrieve.search(course_id, q)}


@router.delete("/{course_id}", status_code=204)
def delete_course(course_id: str, user: dict = Depends(get_current_user)):
    """Delete a course and cascade-delete all of its lectures and notes (owner only)."""
    if not store.delete_course(course_id, owner_id=user["id"]):
        raise HTTPException(404, detail={"code": "course_not_found",
                                         "message": f"No course {course_id}."})
    return Response(status_code=204)
