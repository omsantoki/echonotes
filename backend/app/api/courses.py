"""Course endpoints (contracts/api.md; backs the T021 library)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from app import retrieve, store
from app.models import Course

router = APIRouter(prefix="/api/courses", tags=["courses"])


class CourseIn(BaseModel):
    name: str


@router.post("", status_code=201)
def create_course(body: CourseIn):
    course = store.create_course(Course(name=body.name))
    return {"id": course.id, "name": course.name,
            "created_at": course.created_at.isoformat()}


@router.get("")
def list_courses():
    return [{"id": c["id"], "name": c["name"], "lecture_count": c.get("lecture_count", 0)}
            for c in store.list_courses()]


@router.get("/{course_id}")
def get_course(course_id: str):
    course = store.get_course(course_id)
    if not course:
        raise HTTPException(404, detail={"code": "course_not_found",
                                         "message": f"No course {course_id}."})
    lectures = [{"id": l["id"], "title": l["title"], "date": l.get("date"),
                 "status": l["status"]}
                for l in store.list_lectures(course_id)]
    return {"id": course["id"], "name": course["name"], "lectures": lectures}


@router.get("/{course_id}/search")
def search_course(course_id: str, q: str = ""):
    """Cross-lecture search within a course (Strong, T031/FR-10)."""
    if not store.get_course(course_id):
        raise HTTPException(404, detail={"code": "course_not_found",
                                         "message": f"No course {course_id}."})
    return {"query": q, "results": retrieve.search(course_id, q)}


@router.delete("/{course_id}", status_code=204)
def delete_course(course_id: str):
    """Delete a course and cascade-delete all of its lectures and notes."""
    if not store.delete_course(course_id):
        raise HTTPException(404, detail={"code": "course_not_found",
                                         "message": f"No course {course_id}."})
    return Response(status_code=204)
