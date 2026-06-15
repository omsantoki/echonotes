"""Lecture endpoints (contracts/api.md): ingest (T010), status/document, export (T020).

Feature 002 (Art. X): every route requires an authenticated owner. Ingest verifies the
target course is owned by the caller; fetch/export/delete of a lecture the caller does
not own returns 404 (never 403). Ownership is resolved through the parent course in the
storage layer — here we pass `user["id"]`.
"""

from __future__ import annotations

from fastapi import (APIRouter, BackgroundTasks, Depends, File, Form,
                     HTTPException, UploadFile)
from fastapi.responses import Response

from app import store
from app.auth.deps import get_current_user
from app.ingest import create_and_launch_lecture
from app.render import document_to_html, document_to_markdown

router = APIRouter(prefix="/api/lectures", tags=["lectures"])


@router.post("", status_code=202)
async def create_lecture(bg: BackgroundTasks,
                         course_id: str = Form(...), title: str = Form(...),
                         audio: UploadFile = File(...), slides: UploadFile = File(...),
                         user: dict = Depends(get_current_user)):
    lecture = await create_and_launch_lecture(course_id, title, audio, slides, bg,
                                              owner_id=user["id"])
    return {"lecture_id": lecture.id, "status": "processing"}


@router.get("/{lecture_id}")
def get_lecture(lecture_id: str, user: dict = Depends(get_current_user)):
    lec = _require_lecture(lecture_id, user)
    if lec["status"] != "ready":
        return {"id": lec["id"], "status": lec["status"], "progress": lec.get("progress", "")}
    return {"id": lec["id"], "status": "ready", "title": lec["title"],
            "document": store.assemble_document(lecture_id)}


@router.get("/{lecture_id}/export")
def export_lecture(lecture_id: str, format: str = "md",
                   user: dict = Depends(get_current_user)):
    lec = _require_lecture(lecture_id, user)
    if lec["status"] != "ready":
        raise HTTPException(409, detail={"code": "not_ready",
                                         "message": "Lecture is not ready yet."})
    doc = store.assemble_document(lecture_id)
    if format == "html":
        body, media, ext = document_to_html(lec["title"], doc, standalone=True), "text/html", "html"
    elif format == "md":
        body, media, ext = document_to_markdown(lec["title"], doc), "text/markdown", "md"
    else:
        raise HTTPException(400, detail={"code": "bad_format",
                                         "message": "format must be 'md' or 'html'."})
    filename = _safe_filename(lec["title"], ext)
    return Response(content=body, media_type=media,
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.delete("/{lecture_id}", status_code=204)
def delete_lecture(lecture_id: str, user: dict = Depends(get_current_user)):
    """Delete a lecture along with its notes and preserved diagram images (owner only)."""
    if not store.delete_lecture(lecture_id, owner_id=user["id"]):
        raise HTTPException(404, detail={"code": "lecture_not_found",
                                         "message": f"No lecture {lecture_id}."})
    return Response(status_code=204)


def _require_lecture(lecture_id: str, user: dict) -> dict:
    lec = store.get_lecture(lecture_id, owner_id=user["id"])
    if not lec:
        raise HTTPException(404, detail={"code": "lecture_not_found",
                                         "message": f"No lecture {lecture_id}."})
    return lec


def _safe_filename(title: str, ext: str) -> str:
    base = "".join(c if c.isalnum() or c in " -_" else "_" for c in title).strip()
    return f"{base or 'lecture'}.{ext}"
