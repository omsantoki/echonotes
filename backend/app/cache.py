"""Semantic cache for the RAG Q&A endpoint (Redis-backed).

Students in one course ask the same things many ways ("when's the project due?",
"deadline for the project?"). Each fresh ask costs a vector search + an LLM call. This
cache skips both: it embeds the incoming question and, if a RECENT question in the same
course is within `cache_similarity_threshold` cosine of it, returns that stored answer
instantly. Hits are O(milliseconds) and cost $0.

Design (deliberately simple, for clarity over scale):
  * One Redis list per course, key `semcache:{course_id}`, holding the most recent N
    entries `{vector, query, answer, sources, ts}` as JSON.
  * Lookup does a brute-force cosine over that bounded list (N ~ 200) — no vector index
    needed. Swap in RediSearch / Qdrant if query volume ever outgrows this.
  * Freshness two ways: each entry carries a timestamp and is ignored once older than
    `semantic_cache_ttl` (so time-sensitive answers expire), and the whole key gets that
    TTL as a backstop. `invalidate()` clears a course when a new lecture lands, so new
    content is never masked by a stale answer.
  * Graceful degradation: with no REDIS_URL (local dev) or any Redis error, every call
    no-ops — lookups miss, stores/invalidations are silent — so Q&A always works.
"""

from __future__ import annotations

import json
import time
from functools import lru_cache

import numpy as np

from app.config import get_settings


@lru_cache
def _redis():
    """A Redis client, or None when no REDIS_URL is configured (cache disabled)."""
    url = get_settings().redis_url
    if not url:
        return None
    import redis  # imported lazily so local dev needn't have a server
    return redis.Redis.from_url(url, decode_responses=True)


def _key(course_id: str) -> str:
    return f"semcache:{course_id}"


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0.0 or nb == 0.0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def lookup(course_id: str, query_vec: list[float]) -> dict | None:
    """Return a cached answer payload for a semantically-near recent question, else None."""
    client = _redis()
    if client is None:
        return None
    settings = get_settings()
    try:
        raw = client.lrange(_key(course_id), 0, -1)
    except Exception:
        return None  # Redis unreachable → treat as a miss, never break the request

    q = np.asarray(query_vec, dtype=float)
    now = time.time()
    best, best_sim = None, settings.cache_similarity_threshold
    for item in raw:
        try:
            entry = json.loads(item)
        except (ValueError, TypeError):
            continue
        if now - entry.get("ts", 0) > settings.semantic_cache_ttl:
            continue  # expired entry — ignore (freshness)
        sim = _cosine(q, np.asarray(entry.get("vector", []), dtype=float))
        if sim >= best_sim:
            best, best_sim = entry, sim
    if best is None:
        return None
    return {"answer": best.get("answer", ""), "sources": best.get("sources", []),
            "similarity": round(best_sim, 3)}


def store(course_id: str, query: str, query_vec: list[float],
          answer: str, sources: list[dict]) -> None:
    """Cache a freshly-computed answer for future near-duplicate questions."""
    client = _redis()
    if client is None:
        return
    settings = get_settings()
    entry = json.dumps({"vector": query_vec, "query": query, "answer": answer,
                        "sources": sources, "ts": time.time()})
    key = _key(course_id)
    try:
        pipe = client.pipeline()
        pipe.lpush(key, entry)
        pipe.ltrim(key, 0, settings.semantic_cache_max_per_course - 1)  # bound the set
        pipe.expire(key, settings.semantic_cache_ttl)                   # backstop TTL
        pipe.execute()
    except Exception:
        pass  # caching is best-effort; never fail the request over it


def invalidate(course_id: str) -> None:
    """Drop a course's cache (called when a new lecture becomes ready)."""
    client = _redis()
    if client is None:
        return
    try:
        client.delete(_key(course_id))
    except Exception:
        pass
