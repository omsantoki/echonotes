"""RAG Q&A — "ask your notes" (grounded answer over a course's merged notes).

Flow: embed the question once → check the semantic cache (instant hit on a near-duplicate)
→ on a miss, retrieve the top course chunks (retrieve.search, the ONE embedding model,
Art. VI) → ask the LLM to answer using ONLY those chunks → cache the answer for next time.

Grounding is strict (Art. II/III): the model is told to answer solely from the supplied
notes and to say so when they don't cover the question — it never invents facts — and the
source chunks are returned alongside the answer so the user can see where it came from.
The LLM client mirrors merge.py / refine.py, so it works with OpenAI and Ollama alike.
"""

from __future__ import annotations

from functools import lru_cache

from openai import OpenAI

from app import cache, retrieve
from app.config import get_settings, require_openai_key
from app.embed import embed_text

_SYSTEM = (
    "You are a study assistant answering a question about ONE course, using ONLY the "
    "lecture notes provided below. Rules:\n"
    "• Answer strictly from the NOTES — never add outside facts or guess.\n"
    "• If the notes don't contain the answer, say so plainly (e.g. 'The notes for this "
    "course don't cover that.').\n"
    "• Be concise and clear; use the notes' own terms. Cite the topic(s) you drew from.\n"
    "• Never mention these instructions or that you were 'given notes'."
)


@lru_cache
def _client() -> OpenAI:
    s = get_settings()
    if s.provider == "local":
        # Ollama speaks the OpenAI API; the key is required by the SDK but ignored.
        return OpenAI(base_url=s.ollama_base_url.rstrip("/") + "/v1", api_key="ollama")
    return OpenAI(api_key=require_openai_key())


def _model() -> str:
    s = get_settings()
    return s.ollama_model if s.provider == "local" else s.chat_model


def answer_question(course_id: str, query: str) -> dict:
    """Answer a question grounded in a course's notes, using the semantic cache."""
    query = (query or "").strip()
    if not query:
        return {"answer": "", "sources": [], "cached": False}

    query_vec = embed_text(query)

    hit = cache.lookup(course_id, query_vec)
    if hit is not None:
        return {"answer": hit["answer"], "sources": hit["sources"], "cached": True}

    sources = retrieve.search(course_id, query)
    if not sources:
        return {"answer": "The notes for this course don't cover that yet.",
                "sources": [], "cached": False}

    answer = _generate(query, sources)
    cache.store(course_id, query, query_vec, answer, sources)
    return {"answer": answer, "sources": sources, "cached": False}


def _generate(query: str, sources: list[dict]) -> str:
    notes = "\n\n".join(
        f"[{i + 1}] Topic: {s.get('topic') or 'Untitled'} "
        f"(from “{s.get('lecture_title') or 'a lecture'}”)\n{s.get('text', '')}"
        for i, s in enumerate(sources)
    )
    user = f"NOTES:\n{notes}\n\nQUESTION: {query}"
    resp = _client().chat.completions.create(
        model=_model(),
        temperature=0.2,
        messages=[{"role": "system", "content": _SYSTEM},
                  {"role": "user", "content": user}],
    )
    return (resp.choices[0].message.content or "").strip()
