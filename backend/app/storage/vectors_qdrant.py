"""Qdrant vector backend (managed/cloud, production).

Implements the same VectorBackend contract as the Chroma backends. NoteChunks map
to Qdrant points: the chunk id is the point id, the embedding is the vector, and
the chunk metadata + its text live in the point payload (Qdrant has no separate
"documents" concept).

Correctness note: Qdrant returns cosine *similarity* (higher = closer); the rest
of EchoNotes (retrieve.find_links) expects cosine *distance* (smaller = closer)
and computes `sim = 1 - distance`. So `query()` returns `distance = 1 - score`,
which keeps retrieve.py and the link-similarity threshold unchanged.
"""

from __future__ import annotations

from functools import lru_cache

from qdrant_client import QdrantClient
from qdrant_client import models as qm

from app.config import get_settings
from app.models import NoteChunk


@lru_cache
def _client() -> QdrantClient:
    s = get_settings()
    # Explicit, generous timeout: vector upserts cross regions (local/Render -> Qdrant
    # Cloud), where the client's short default can surface as "write operation timed out".
    return QdrantClient(url=s.qdrant_url, api_key=s.qdrant_api_key or None,
                        timeout=s.qdrant_timeout)


class QdrantVectors:
    @property
    def _name(self) -> str:
        return get_settings().qdrant_collection or "notechunks"

    def _ensure(self, dim: int) -> None:
        client = _client()
        if client.collection_exists(self._name):
            return
        client.create_collection(
            collection_name=self._name,
            vectors_config=qm.VectorParams(size=dim, distance=qm.Distance.COSINE),
        )
        # Payload indexes so course/lecture filters stay fast.
        for field in ("course_id", "lecture_id"):
            client.create_payload_index(
                self._name, field_name=field, field_schema=qm.PayloadSchemaType.KEYWORD
            )

    def add(self, chunks: list[NoteChunk]) -> None:
        if not chunks:
            return
        self._ensure(len(chunks[0].embedding))
        points = [
            qm.PointStruct(
                id=c.id,
                vector=c.embedding,
                payload={**c.metadata(), "text": c.text},
            )
            for c in chunks
        ]
        _client().upsert(collection_name=self._name, points=points)

    def query(self, course_id, query_embedding, n, exclude_lecture_id) -> list[dict]:
        if not _client().collection_exists(self._name):
            return []
        must = [qm.FieldCondition(key="course_id", match=qm.MatchValue(value=course_id))]
        must_not = (
            [qm.FieldCondition(key="lecture_id", match=qm.MatchValue(value=exclude_lecture_id))]
            if exclude_lecture_id
            else None
        )
        res = _client().query_points(
            collection_name=self._name,
            query=query_embedding,
            limit=n,
            with_payload=True,
            query_filter=qm.Filter(must=must, must_not=must_not),
        )
        out: list[dict] = []
        for pt in res.points:
            payload = dict(pt.payload or {})
            text = payload.pop("text", "")
            out.append({
                "id": str(pt.id),
                "text": text,
                "metadata": payload,
                "distance": 1.0 - pt.score,  # similarity -> distance for retrieve.py
            })
        return out

    def list_by_lecture(self, lecture_id) -> list[dict]:
        if not _client().collection_exists(self._name):
            return []
        flt = qm.Filter(
            must=[qm.FieldCondition(key="lecture_id", match=qm.MatchValue(value=lecture_id))]
        )
        rows: list[dict] = []
        offset = None
        while True:
            points, offset = _client().scroll(
                collection_name=self._name,
                scroll_filter=flt,
                with_payload=True,
                limit=256,
                offset=offset,
            )
            for pt in points:
                payload = dict(pt.payload or {})
                text = payload.pop("text", "")
                rows.append({"id": str(pt.id), "text": text, "metadata": payload})
            if offset is None:
                break
        return sorted(rows, key=lambda r: r["metadata"].get("order", 0))

    def update_text(self, chunk_id, text, embedding) -> None:
        # Re-set only the text payload + the vector; keep the rest of the payload.
        _client().set_payload(
            collection_name=self._name, payload={"text": text}, points=[chunk_id]
        )
        _client().update_vectors(
            collection_name=self._name,
            points=[qm.PointVectors(id=chunk_id, vector=embedding)],
        )

    def delete_by_lecture(self, lecture_id) -> None:
        if not _client().collection_exists(self._name):
            return
        _client().delete(
            collection_name=self._name,
            points_selector=qm.FilterSelector(
                filter=qm.Filter(
                    must=[qm.FieldCondition(key="lecture_id", match=qm.MatchValue(value=lecture_id))]
                )
            ),
        )
