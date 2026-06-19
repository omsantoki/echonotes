## Why

Students repeatedly ask the same questions about a course ("when is the project due?", "explain backprop"), but the product only offered raw chunk *search* — no synthesized answer — and every query re-ran embedding + vector search with no caching. Adding a grounded RAG answer endpoint makes the notes directly answerable, and a semantic cache in front of it serves near-duplicate questions instantly at near-zero cost.

## What Changes

- New endpoint `GET /api/courses/{id}/ask?q=...` returns a grounded LLM answer plus its source chunks: `{ query, answer, sources, cached }`. Owner-scoped (404 for non-owners), gated by `ENABLE_QA` (503 when disabled).
- The answer is generated **only** from the top retrieved course chunks (reusing `retrieve.search` and the one embedding model); the model is instructed to say when the notes don't cover the question and never to invent facts.
- A **Redis semantic cache** fronts the answer path: the incoming question is embedded once, and if a recent question in the same course is within a cosine threshold, its stored answer is returned without retrieval or an LLM call.
- Cache freshness: per-entry TTL plus a key TTL backstop, a bounded per-course set, and invalidation of a course's cache whenever a new lecture becomes `ready`.
- Graceful degradation: with no `REDIS_URL`, the cache no-ops (every ask is a miss) and Q&A still works.
- Frontend: an "Ask your notes" panel on the course page with a "cached" badge when the cache served the answer.

## Capabilities

### New Capabilities
- `qa-semantic-cache`: grounded RAG question-answering over a course's notes, fronted by a Redis semantic cache (similarity-threshold hit, TTL freshness, per-course invalidation, no-op without Redis), with the answer endpoint gated/owner-scoped.

### Modified Capabilities
<!-- none: reuses cross-lecture-retrieval and configuration-and-health without changing their requirements -->

## Impact

- Code: `backend/app/answer.py` (new), `backend/app/cache.py` (new), `backend/app/api/courses.py` (`/ask` route), `backend/app/pipeline.py` (cache invalidation on `ready`), `backend/app/config.py` (`enable_qa`, `cache_similarity_threshold`, `semantic_cache_ttl`, `semantic_cache_max_per_course`).
- Frontend: `useAsk` hook, `AskPanel` component, `askCourse` API method + `AskResponse` type, wired into the course page.
- Dependencies: Redis (shared with the async-pipeline change); `fakeredis` for tests.
- Reuses `retrieve.search`, `embed_text` (one embedding model, Art. VI), and the merge/refine LLM client pattern.
