## Context

The course page previously exposed only `GET /api/courses/{id}/search`, which returns raw note chunks via `retrieve.search` — no synthesized answer. A semantic cache only pays off when there is an expensive operation to skip, so this change first adds a real RAG answer path, then caches it. Redis is already introduced by the `async-pipeline` change, so the cache adds no new infrastructure.

## Goals / Non-Goals

**Goals:**
- A grounded "ask your notes" answer that never invents facts and cites its sources.
- Instant, $0 answers for near-duplicate questions within a course.
- Correct freshness: time-sensitive answers expire, and new lectures don't get masked by stale cache.
- Works with zero extra setup locally (no Redis → cache no-ops).

**Non-Goals:**
- A vector-indexed cache (RediSearch/Qdrant) — brute-force over a bounded per-course list is enough at current scale.
- Multi-turn chat / conversation memory.
- Caching the existing `/search` (chunk) endpoint.

## Decisions

- **Reuse the retrieval + embedding + LLM-client stack.** Answers ground on `retrieve.search` (the one embedding model, Art. VI, course-scoped) and generate via the same OpenAI/Ollama client pattern as `merge.py`/`refine.py`. No new model wiring.
- **Strict grounding prompt.** The system prompt restricts the answer to the supplied notes, requires "say when not covered," and forbids invented facts — matching the project's provenance/faithfulness articles. Source chunks are returned alongside the answer.
- **Redis list per course, brute-force cosine.** Key `semcache:{course_id}` holds the most recent N `{vector, query, answer, sources, ts}` entries. Lookup embeds the question once and scans for the best entry at/above `cache_similarity_threshold`. Chosen over a vector index for clarity and zero extra infra; the upgrade path (RediSearch/Qdrant) is noted.
- **Two-layer freshness.** Each entry carries a timestamp and is ignored past `semantic_cache_ttl`; the key also gets that TTL as a backstop; and `cache.invalidate(course_id)` clears the course when a new lecture reaches `ready` (called from the pipeline). This prevents a stale "due date" answer and prevents new content being masked.
- **Graceful no-op without Redis.** `_redis()` returns `None` when `redis_url` is blank or on any connection error; `lookup` then misses and `store`/`invalidate` do nothing, so Q&A degrades to "always compute" rather than failing.
- **Gating + scoping.** `/ask` reuses the existing owner check (`_require_owned_course`, 404 not 403) and returns 503 when `ENABLE_QA` is false.

## Risks / Trade-offs

- [Cache serves a subtly-wrong answer for a differently-intended but lexically-near question] → High threshold (0.95 default) + TTL + per-course scoping bound the blast radius; threshold is configurable.
- [Brute-force scan cost grows with cache size] → Bounded by `semantic_cache_max_per_course` (LTRIM); revisit with a vector index if volume grows (logged as the upgrade path).
- [LLM hallucination despite grounding] → Strict prompt + returning sources so the user can verify; not a hard guarantee.
- [Redis outage] → Cache no-ops; answers still computed. Surfaced via `/api/health` `async.cache`.

## Migration Plan

1. Ship with `ENABLE_QA=true`; with no `REDIS_URL` the cache is inert and `/ask` computes every time.
2. Set `REDIS_URL` (shared with the task queue) to activate caching — no schema/data migration.
3. Rollback: set `ENABLE_QA=false` (endpoint 503s) or unset `REDIS_URL` (cache off); no persistent state to undo.

## Open Questions

- Should answers themselves carry a confidence/coverage signal in the response? (Deferred.)
