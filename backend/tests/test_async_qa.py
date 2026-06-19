"""Tests for the async task queue + semantic-cached RAG Q&A.

Hermetic like the rest of the suite: no real Redis (fakeredis), no real worker
(the pipeline is mocked / the task is intercepted), no real embedding model or LLM
(both monkeypatched — the test image excludes the heavy ML stack). We assert the
contract: uploads ENQUEUE rather than run inline; the semantic cache hits on a
near-duplicate, misses below threshold / after TTL / after invalidation, and no-ops
without Redis; the RAG path answers, caches, and short-circuits on a hit; and /ask
is owner-scoped + gated by ENABLE_QA.
"""

from __future__ import annotations

import fakeredis

from app import answer, cache, ingest, store
from app.config import get_settings
from app.models import Course, User
from tests.conftest import auth_headers


# --------------------------------------------------------------------------- #
# Part A — uploads enqueue the pipeline (don't run it inline in the request)
# --------------------------------------------------------------------------- #

class _FakeTask:
    def __init__(self):
        self.calls = []

    def delay(self, *args):
        self.calls.append(args)


def test_upload_enqueues_pipeline_and_returns_202(client, register, monkeypatch):
    fake = _FakeTask()
    monkeypatch.setattr(ingest, "process_lecture", fake)

    token = register("q@example.com")["session_token"]
    cid = client.post("/api/courses", json={"name": "C"},
                      headers=auth_headers(token)).json()["id"]

    r = client.post(
        "/api/lectures",
        data={"course_id": cid, "title": "L"},
        files={"audio": ("a.mp3", b"FAKE", "audio/mpeg"),
               "slides": ("s.pdf", b"%PDF-1.4 fake", "application/pdf")},
        headers=auth_headers(token),
    )
    assert r.status_code == 202, r.text
    lecture_id = r.json()["lecture_id"]
    # The heavy pipeline was ENQUEUED, not executed in the request.
    assert len(fake.calls) == 1
    assert fake.calls[0][0] == lecture_id          # first arg is the lecture id
    assert store.get_lecture(lecture_id)["status"] == "processing"


# --------------------------------------------------------------------------- #
# Part B — semantic cache (unit, fakeredis)
# --------------------------------------------------------------------------- #

def _use_fake_redis(monkeypatch):
    fake = fakeredis.FakeStrictRedis(decode_responses=True)
    monkeypatch.setattr(cache, "_redis", lambda: fake)
    return fake


def test_cache_hit_on_near_duplicate(monkeypatch):
    _use_fake_redis(monkeypatch)
    v = [1.0, 0.0, 0.0]
    cache.store("c1", "when is the project due", v, "Friday", [{"topic": "admin"}])

    near = [0.99, 0.01, 0.0]          # cosine ≈ 1.0, above the 0.95 default threshold
    hit = cache.lookup("c1", near)
    assert hit is not None
    assert hit["answer"] == "Friday"
    assert hit["sources"] == [{"topic": "admin"}]


def test_cache_miss_below_threshold(monkeypatch):
    _use_fake_redis(monkeypatch)
    cache.store("c1", "q", [1.0, 0.0, 0.0], "A", [])
    assert cache.lookup("c1", [0.0, 1.0, 0.0]) is None   # orthogonal → cosine 0


def test_cache_scoped_per_course(monkeypatch):
    _use_fake_redis(monkeypatch)
    cache.store("c1", "q", [1.0, 0.0, 0.0], "A", [])
    assert cache.lookup("c2", [1.0, 0.0, 0.0]) is None   # other course's cache is separate


def test_cache_entry_expires_after_ttl(monkeypatch):
    _use_fake_redis(monkeypatch)
    clock = {"t": 1000.0}
    monkeypatch.setattr(cache.time, "time", lambda: clock["t"])
    cache.store("c1", "q", [1.0, 0.0, 0.0], "A", [])

    clock["t"] += get_settings().semantic_cache_ttl + 1    # jump past the TTL
    assert cache.lookup("c1", [1.0, 0.0, 0.0]) is None     # stale entry ignored


def test_cache_invalidate_clears_course(monkeypatch):
    _use_fake_redis(monkeypatch)
    cache.store("c1", "q", [1.0, 0.0, 0.0], "A", [])
    cache.invalidate("c1")
    assert cache.lookup("c1", [1.0, 0.0, 0.0]) is None


def test_cache_noop_without_redis(monkeypatch):
    monkeypatch.setattr(cache, "_redis", lambda: None)   # no REDIS_URL configured
    cache.store("c1", "q", [1.0, 0.0, 0.0], "A", [])     # must not raise
    cache.invalidate("c1")                               # must not raise
    assert cache.lookup("c1", [1.0, 0.0, 0.0]) is None   # always a miss


# --------------------------------------------------------------------------- #
# Part B — RAG answer flow (cache short-circuits the LLM)
# --------------------------------------------------------------------------- #

def test_answer_caches_and_short_circuits_llm(monkeypatch):
    _use_fake_redis(monkeypatch)
    monkeypatch.setattr(answer, "embed_text", lambda _q: [1.0, 0.0, 0.0])
    monkeypatch.setattr(answer.retrieve, "search",
                        lambda cid, q: [{"topic": "T", "lecture_title": "L", "text": "Body"}])
    gen_calls = {"n": 0}

    def fake_generate(query, sources):
        gen_calls["n"] += 1
        return "Generated answer"

    monkeypatch.setattr(answer, "_generate", fake_generate)

    first = answer.answer_question("c1", "explain topic T")
    assert first["cached"] is False and first["answer"] == "Generated answer"
    assert gen_calls["n"] == 1

    second = answer.answer_question("c1", "explain topic T")   # same → cache hit
    assert second["cached"] is True and second["answer"] == "Generated answer"
    assert gen_calls["n"] == 1                                  # LLM NOT called again


def test_answer_no_notes_message(monkeypatch):
    monkeypatch.setattr(cache, "_redis", lambda: None)
    monkeypatch.setattr(answer, "embed_text", lambda _q: [1.0, 0.0, 0.0])
    monkeypatch.setattr(answer.retrieve, "search", lambda cid, q: [])
    out = answer.answer_question("c1", "anything")
    assert out["cached"] is False and out["sources"] == []
    assert "don't cover that" in out["answer"]


# --------------------------------------------------------------------------- #
# Part B — /ask endpoint: owner-scoped + gated by ENABLE_QA
# --------------------------------------------------------------------------- #

def test_ask_endpoint_returns_answer(client, register, monkeypatch):
    monkeypatch.setattr(answer, "answer_question",
                        lambda cid, q: {"answer": "42", "sources": [], "cached": False})
    token = register("a@example.com")["session_token"]
    cid = client.post("/api/courses", json={"name": "C"},
                      headers=auth_headers(token)).json()["id"]
    r = client.get(f"/api/courses/{cid}/ask?q=meaning", headers=auth_headers(token))
    assert r.status_code == 200, r.text
    assert r.json() == {"query": "meaning", "answer": "42", "sources": [], "cached": False}


def test_ask_cross_tenant_is_404(client, register):
    a = register("a@example.com")["session_token"]
    b = register("b@example.com")["session_token"]
    cid = client.post("/api/courses", json={"name": "Private"},
                      headers=auth_headers(a)).json()["id"]
    # B probing A's course → 404 (existence not leaked), and no LLM is reached.
    assert client.get(f"/api/courses/{cid}/ask?q=x", headers=auth_headers(b)).status_code == 404


def test_ask_disabled_returns_503(client, register, monkeypatch):
    monkeypatch.setenv("ENABLE_QA", "false")
    get_settings.cache_clear()
    token = register("a@example.com")["session_token"]
    cid = client.post("/api/courses", json={"name": "C"},
                      headers=auth_headers(token)).json()["id"]
    r = client.get(f"/api/courses/{cid}/ask?q=x", headers=auth_headers(token))
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "qa_disabled"
