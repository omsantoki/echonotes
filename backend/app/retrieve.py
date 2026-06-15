"""Cross-lecture retrieval / search (task T031, FR-10 — Strong).

Embeds the query with the ONE embedding model (Art. VI) and queries the vector store
scoped to a single course (Art. V), returning the top matching note segments across
all of that course's lectures, each with its source label. The result count is capped
(retrieve_top_n) per the constitution's "keep retrieved context to the top few" intent.

This module also backs the Stretch context-retrieval during merge (T040).
"""

from __future__ import annotations

from app import store
from app.config import get_settings
from app.embed import embed_text


def search(course_id: str, query: str, n: int | None = None) -> list[dict]:
    """Top matching note segments across a course's lectures for a text query."""
    query = (query or "").strip()
    if not query:
        return []
    n = n or get_settings().retrieve_top_n
    results: list[dict] = []
    for hit in store.query(course_id, embed_text(query), n=n):
        meta = hit.get("metadata", {})
        lecture = store.get_lecture(meta.get("lecture_id", "")) or {}
        results.append({
            "lecture_id": meta.get("lecture_id"),
            "lecture_title": lecture.get("title", ""),
            "topic": meta.get("topic"),
            "text": hit.get("text", ""),
            "source_type": meta.get("source_type"),
        })
    return results


def find_links(course_id: str, topics: list[tuple[str, str]],
               exclude_lecture_id: str | None = None) -> dict:
    """Link each current topic to the most similar EARLIER lecture (Stretch, T040/T041).

    `topics` is a list of (topic_title, combined_text). Returns
    {topic_title: {lecture_id, lecture_title, topic, similarity}} only for topics whose
    best prior match clears `link_min_similarity`. Retrieval is capped at retrieve_top_n
    and uses the ONE embedding model (Art. VI); links carry their similarity as evidence
    (Art. II); scoped to the course (Art. V).
    """
    settings = get_settings()
    if not settings.link_lectures:
        return {}
    n = settings.retrieve_top_n
    min_sim = settings.link_min_similarity
    out: dict = {}
    for title, text in topics:
        text = (text or "").strip()
        if not text:
            continue
        for hit in store.query(course_id, embed_text(text), n=n,
                               exclude_lecture_id=exclude_lecture_id):
            dist = hit.get("distance")
            sim = (1.0 - dist) if dist is not None else None
            if sim is None or sim < min_sim:
                continue
            meta = hit.get("metadata", {})
            lecture = store.get_lecture(meta.get("lecture_id", "")) or {}
            out[title] = {
                "lecture_id": meta.get("lecture_id"),
                "lecture_title": lecture.get("title", ""),
                "topic": meta.get("topic"),
                "similarity": round(float(sim), 3),
            }
            break  # strongest qualifying prior match wins
    return out
