"""Minimal server-rendered UI (tasks T019, T021).

The document is the star (Art. IX): create a course, upload a lecture, watch
progress, read the merged source-labeled notes, browse the per-course library,
export. Forms post to thin /web routes that reuse the same ingestion path as the
JSON API, so there is no second pipeline.
"""

from __future__ import annotations

import html

from fastapi import APIRouter, BackgroundTasks, File, Form, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse

from app import retrieve, store
from app.auth import service as auth_service
from app.ingest import create_and_launch_lecture
from app.models import Course
from app.render import document_to_html, page

router = APIRouter(tags=["web"])

_SRC_TAG = {"slides": "📄 slides", "spoken": "🎙 spoken", "diagram": "📊 diagram"}


def _owner_id() -> str:
    """The single owner this server-rendered console operates as (feature 002, Art. X).

    The multi-tenant product surface is the React SPA + JSON API (gated per user). This
    built-in console is a single-tenant local/admin view bound to the bootstrap admin, so
    it is always owner-scoped and never lists another user's data.
    """
    return auth_service.ensure_bootstrap_admin()["id"]


@router.get("/", response_class=HTMLResponse)
def home():
    courses = store.list_courses(owner_id=_owner_id())
    course_items = "".join(
        f'<li><a href="/courses/{c["id"]}">{html.escape(c["name"])}</a> '
        f'<span class="muted">({c.get("lecture_count", 0)} lectures)</span></li>'
        for c in courses
    ) or '<li class="muted">No courses yet.</li>'

    if courses:
        options = "".join(
            f'<option value="{c["id"]}">{html.escape(c["name"])}</option>' for c in courses
        )
        upload_form = (
            '<form method="post" action="/web/lectures" enctype="multipart/form-data">'
            f'<label>Course <select name="course_id" required>{options}</select></label>'
            '<label>Title <input name="title" placeholder="L05 — Entropy" required/></label>'
            '<label>Audio <input type="file" name="audio" accept="audio/*" required/></label>'
            '<label>Slides PDF <input type="file" name="slides" accept="application/pdf" required/></label>'
            '<button>Merge lecture</button></form>'
        )
    else:
        upload_form = '<p class="muted">Create a course first.</p>'

    body = (
        '<h1>EchoNotes</h1>'
        '<p class="muted">Merge what was <em>said</em> with what was on the <em>slides</em>.</p>'
        '<section class="card"><h2>Courses</h2>'
        f'<ul>{course_items}</ul>'
        '<form method="post" action="/web/courses" class="row">'
        '<input name="name" placeholder="New course name" required/>'
        '<button>Create course</button></form></section>'
        f'<section class="card"><h2>Add a lecture</h2>{upload_form}</section>'
    )
    return HTMLResponse(page("EchoNotes", body))


@router.post("/web/courses")
def web_create_course(name: str = Form(...)):
    store.create_course(Course(name=name, owner_id=_owner_id()))
    return RedirectResponse("/", status_code=303)


@router.post("/web/lectures")
async def web_create_lecture(bg: BackgroundTasks, course_id: str = Form(...),
                             title: str = Form(...), audio: UploadFile = File(...),
                             slides: UploadFile = File(...)):
    lecture = await create_and_launch_lecture(course_id, title, audio, slides, bg,
                                              owner_id=_owner_id())
    return RedirectResponse(f"/lectures/{lecture.id}", status_code=303)


def _search_html(course_id: str, q: str) -> str:
    """Cross-lecture search box + results for the course page (T031)."""
    form = (f'<form method="get" action="/courses/{course_id}" class="row">'
            f'<input name="q" value="{html.escape(q)}" placeholder="Search this course…" style="flex:1"/>'
            f'<button>Search</button></form>')
    if not q.strip():
        return f'<section class="card"><h2>Search</h2>{form}</section>'
    results = retrieve.search(course_id, q)
    if not results:
        rows = '<p class="muted">No matches.</p>'
    else:
        rows = "".join(
            f'<div class="result" style="margin:.6em 0">'
            f'<a href="/lectures/{r["lecture_id"]}">{html.escape(r["lecture_title"] or "lecture")}</a> '
            f'<span class="muted">· {html.escape(r["topic"] or "")}</span> '
            f'<span class="badge">{_SRC_TAG.get(r["source_type"], html.escape(r["source_type"] or ""))}</span>'
            f'<div>{html.escape((r["text"] or "")[:280])}</div></div>'
            for r in results
        )
    return f'<section class="card"><h2>Search</h2>{form}{rows}</section>'


@router.get("/courses/{course_id}", response_class=HTMLResponse)
def course_page(course_id: str, q: str = ""):
    course = store.get_course(course_id, owner_id=_owner_id())
    if not course:
        return HTMLResponse(page("Not found", '<p>Course not found.</p>'), status_code=404)
    items = "".join(
        f'<li><a href="/lectures/{l["id"]}">{html.escape(l["title"])}</a> '
        f'<span class="badge status-{l["status"]}">{l["status"]}</span></li>'
        for l in store.list_lectures(course_id)
    ) or '<li class="muted">No lectures yet.</li>'
    body = (f'<p><a href="/">← all courses</a></p><h1>{html.escape(course["name"])}</h1>'
            f'{_search_html(course_id, q)}<h2>Lectures</h2><ul>{items}</ul>')
    return HTMLResponse(page(course["name"], body))


@router.get("/lectures/{lecture_id}", response_class=HTMLResponse)
def lecture_page(lecture_id: str):
    lec = store.get_lecture(lecture_id, owner_id=_owner_id())
    if not lec:
        return HTMLResponse(page("Not found", '<p>Lecture not found.</p>'), status_code=404)
    title = html.escape(lec["title"])

    if lec["status"] != "ready":
        # Auto-refresh while processing so progress updates without a manual reload.
        refresh = '<meta http-equiv="refresh" content="3">' if lec["status"] == "processing" else ""
        fail = '' if lec["status"] != "failed" else '<p class="fail">Processing failed.</p>'
        body = (f'{refresh}<h1>{title}</h1><p class="muted">Status: {lec["status"]}</p>'
                f'<div class="progress">{html.escape(lec.get("progress", "") or lec["status"])}</div>'
                f'{fail}<p><a href="/courses/{lec["course_id"]}">← course</a></p>')
        return HTMLResponse(page(title, body))

    doc = store.assemble_document(lecture_id)
    export = (f'<div class="row">'
              f'<a class="button" href="/api/lectures/{lecture_id}/export?format=md">⬇ Markdown</a>'
              f'<a class="button" href="/api/lectures/{lecture_id}/export?format=html">⬇ HTML</a></div>')
    body = (f'<p><a href="/courses/{lec["course_id"]}">← course</a></p><h1>{title}</h1>'
            f'{export}{document_to_html(lec["title"], doc)}')
    return HTMLResponse(page(title, body))
