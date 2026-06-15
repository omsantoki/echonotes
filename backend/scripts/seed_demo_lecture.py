"""Seed a realistic, ready-to-read course WITHOUT the heavy pipeline.

Frontend dev helper: builds two ready lectures (with spoken-only highlights, a
diagram, and a cross-lecture "builds on" link) using only the embedding model —
no Whisper, no Ollama. Run:  python scripts/seed_demo_lecture.py
"""

from __future__ import annotations

import datetime as dt

from app import store
from app.embed import embed_texts
from app.models import Course, DiagramAsset, Lecture, LectureStatus, NoteChunk, SourceType

SPOKEN_PREFIX = "★ Spoken-only (not on the slides) — "

DIAGRAM_SVG = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 480 220">
  <rect width="480" height="220" fill="#f8fafc"/>
  <rect x="20" y="40" width="440" height="140" rx="10" fill="#ecfeff" stroke="#7c3aed" stroke-width="2"/>
  <text x="240" y="30" text-anchor="middle" font-family="sans-serif" font-size="14" fill="#7c3aed">Thylakoid membrane</text>
  <rect x="50" y="80" width="90" height="60" rx="8" fill="#dbeafe" stroke="#2563eb"/>
  <text x="95" y="115" text-anchor="middle" font-family="sans-serif" font-size="13" fill="#1e3a8a">PS II</text>
  <rect x="200" y="80" width="90" height="60" rx="8" fill="#dbeafe" stroke="#2563eb"/>
  <text x="245" y="115" text-anchor="middle" font-family="sans-serif" font-size="13" fill="#1e3a8a">Cyt b6f</text>
  <rect x="350" y="80" width="90" height="60" rx="8" fill="#fef3c7" stroke="#b45309"/>
  <text x="395" y="115" text-anchor="middle" font-family="sans-serif" font-size="13" fill="#7c2d12">ATP synthase</text>
  <line x1="140" y1="110" x2="200" y2="110" stroke="#334155" stroke-width="2" marker-end="url(#a)"/>
  <line x1="290" y1="110" x2="350" y2="110" stroke="#334155" stroke-width="2" marker-end="url(#a)"/>
  <defs><marker id="a" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
    <path d="M0,0 L6,3 L0,6 Z" fill="#334155"/></marker></defs>
</svg>"""


def _chunks(lecture_id: str, course_id: str, spec: list[tuple]) -> list[NoteChunk]:
    chunks = []
    for order, (topic, source, text, spoken, reason, diagram_ref) in enumerate(spec):
        full_reason = (SPOKEN_PREFIX + reason) if spoken else reason
        chunks.append(
            NoteChunk(
                lecture_id=lecture_id, course_id=course_id, topic=topic, order=order,
                text=text, source_type=SourceType(source), reason=full_reason,
                confidence=0.92, diagram_ref=diagram_ref,
            )
        )
    return chunks


def _persist(chunks: list[NoteChunk]) -> None:
    for chunk, vec in zip(chunks, embed_texts([c.text for c in chunks])):
        chunk.embedding = vec
    store.add_chunks(chunks)


def main() -> None:
    # Own the seeded course (feature 002, Art. X) so it shows up for a real user. The
    # bootstrap admin is the simplest owner; claim it via forgot-password to log in and
    # see this course, or reassign owner_id to your own signed-up user.
    from app.auth.service import ensure_bootstrap_admin
    owner = ensure_bootstrap_admin()
    course = store.create_course(
        Course(name="Biology 101 — Photosynthesis (demo)", owner_id=owner["id"]))
    print(f"Seeded course owned by {owner['email']} "
          f"(claim it with forgot-password to log in and view it).")

    # --- Lecture A: the earlier lecture that Lecture B builds on ---
    lec_a = Lecture(course_id=course.id, title="Lecture 2 — The Photosynthetic Membrane",
                    date=dt.date(2026, 5, 1), status=LectureStatus.ready, progress="Ready.")
    store.create_lecture(lec_a)
    _persist(_chunks(lec_a.id, course.id, [
        ("Overview", "slides",
         "Photosynthesis occurs inside the **chloroplast**, across stacked thylakoid membranes.",
         False, "From slides section 'Overview'.", None),
        ("Overview", "spoken",
         "Think of a thylakoid as a flattened sac — a stack of them is called a granum.",
         True, "Matched to 'Overview' by similarity (0.90).", None),
    ]))

    # --- Lecture B: diagram + spoken-only + a cross-lecture "builds on" link ---
    lec_b = Lecture(course_id=course.id, title="Lecture 5 — Light Reactions & the Calvin Cycle",
                    date=dt.date(2026, 5, 15), status=LectureStatus.ready, progress="Ready.")
    store.create_lecture(lec_b)

    diagram = DiagramAsset(lecture_id=lec_b.id, image_ref="", section_topic="Light Reactions",
                           description="Light-dependent reactions in the thylakoid membrane.")
    diagram.image_ref = store.save_diagram_image(lec_b.id, diagram.id, "svg", DIAGRAM_SVG)
    store.create_diagram(diagram)

    _persist(_chunks(lec_b.id, course.id, [
        ("Light Reactions", "slides",
         "The thylakoid membrane is where light energy is converted into chemical energy.",
         False, "From slides section 'Light Reactions'.", None),
        ("Light Reactions", "slides",
         "**Photosystem II** contains the reaction-center chlorophyll **P680**, named for its peak absorption at 680 nm.",
         False, "From slides section 'Light Reactions'.", None),
        ("Light Reactions", "spoken",
         "Water is split into oxygen, hydrogen ions, and electrons — a process called photolysis.",
         True, "Matched to 'Light Reactions' by similarity (0.91); top-1 of 8 slide sections.", None),
        ("Light Reactions", "slides",
         "- ATP is produced by chemiosmosis across the thylakoid membrane.",
         False, "From slides bullet list.", None),
        ("Light Reactions", "slides",
         "- NADPH carries high-energy electrons to the Calvin cycle.",
         False, "From slides bullet list.", None),
        ("Light Reactions", "diagram",
         "The light-dependent reactions in the thylakoid membrane: electron transport through PS II and Cyt b6f, ending at ATP synthase.",
         False, "Preserved from this slide section (US-3). Description generated by a vision model (US-5).", diagram.id),
        ("The Calvin Cycle", "slides",
         "Carbon dioxide is fixed by the enzyme **Rubisco** into 3-phosphoglycerate (3-PG).",
         False, "From slides section 'The Calvin Cycle'.", None),
        ("The Calvin Cycle", "spoken",
         "Rubisco is the most abundant protein on Earth — that's why this single step is such a big deal.",
         True, "Matched to 'The Calvin Cycle' by similarity (0.88).", None),
        ("The Calvin Cycle", "slides",
         "3-PG is reduced to **glyceraldehyde-3-phosphate (G3P)** using the ATP and NADPH from the light reactions.",
         False, "From slides section 'The Calvin Cycle'.", None),
    ]))

    store.set_lecture_links(lec_b.id, {
        "Light Reactions": {
            "lecture_id": lec_a.id,
            "lecture_title": "Lecture 2 — The Photosynthetic Membrane",
            "topic": "Overview",
            "similarity": 0.88,
        }
    })

    print(f"course_id={course.id}")
    print(f"lecture_a={lec_a.id}")
    print(f"lecture_b={lec_b.id}  <-- open this one (diagram + spoken-only + builds-on)")


if __name__ == "__main__":
    main()
