<!-- Code is already implemented and tested; boxes are checked to reflect completed work. -->

## 1. Config

- [x] 1.1 Add `enable_qa`, `cache_similarity_threshold`, `semantic_cache_ttl`, `semantic_cache_max_per_course` to `backend/app/config.py`
- [x] 1.2 Document the new env vars in `backend/.env.example`

## 2. Semantic cache

- [x] 2.1 Create `backend/app/cache.py`: per-course Redis list, brute-force cosine `lookup`, `store` (LPUSH + LTRIM + key TTL), `invalidate`, no-op without Redis
- [x] 2.2 Per-entry TTL (timestamp) plus key-TTL backstop

## 3. RAG answer path

- [x] 3.1 Create `backend/app/answer.py`: embed → cache lookup → on miss `retrieve.search` → grounded LLM answer (merge/refine client pattern) → cache store
- [x] 3.2 Strict grounding prompt (answer only from notes; say when not covered; no invented facts)

## 4. Endpoint + invalidation

- [x] 4.1 Add `GET /api/courses/{id}/ask` to `backend/app/api/courses.py` — owner-scoped, gated by `enable_qa` (503 `qa_disabled`)
- [x] 4.2 Invalidate the course cache in `backend/app/pipeline.py` when a lecture reaches `ready`

## 5. Frontend

- [x] 5.1 Add `AskResponse` type and `api.askCourse` (`frontend/src/types/api.ts`, `frontend/src/lib/api.ts`)
- [x] 5.2 Add `useAsk` hook and `AskPanel` component with a "cached" badge; wire into the course page

## 6. Tests

- [x] 6.1 Cache unit tests: hit/miss/threshold/scope/TTL/invalidate/no-Redis (`backend/tests/test_async_qa.py`)
- [x] 6.2 Answer tests: cache short-circuits the LLM; no-notes message
- [x] 6.3 Endpoint tests: returns answer shape; cross-tenant 404; disabled 503
- [x] 6.4 Frontend typecheck + tests green

## 7. Manual verification (Redis mode)

- [ ] 7.1 With `REDIS_URL` set, ask a question (`cached:false`), repeat a near-duplicate (`cached:true`, no LLM call in logs); upload a new lecture and confirm the next ask misses; stop Redis and confirm asks still answer
