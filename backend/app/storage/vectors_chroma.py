"""Chroma vector backends — local (PersistentClient) and remote (HttpClient).

The local backend is EchoNotes' default; behavior is byte-identical to the
original store.py. The remote backend is the near-zero-code path to a managed
vector store (a hosted Chroma server) and shares all query/add/delete logic.
"""

from __future__ import annotations

from urllib.parse import urlparse

from app.config import get_settings
from app.models import NoteChunk

_NOTES_COLLECTION = "notechunks"


class _ChromaBase:
    def _client(self):  # pragma: no cover - overridden
        raise NotImplementedError

    def _collection(self):
        return self._client().get_or_create_collection(
            name=_NOTES_COLLECTION, metadata={"hnsw:space": "cosine"}
        )

    def add(self, chunks: list[NoteChunk]) -> None:
        self._collection().add(
            ids=[c.id for c in chunks],
            embeddings=[c.embedding for c in chunks],
            documents=[c.text for c in chunks],
            metadatas=[c.metadata() for c in chunks],
        )

    def query(self, course_id, query_embedding, n, exclude_lecture_id) -> list[dict]:
        where: dict = {"course_id": course_id}
        if exclude_lecture_id:
            where = {"$and": [{"course_id": course_id},
                              {"lecture_id": {"$ne": exclude_lecture_id}}]}
        res = self._collection().query(
            query_embeddings=[query_embedding], n_results=n, where=where
        )
        out: list[dict] = []
        if not res["ids"] or not res["ids"][0]:
            return out
        for i, chunk_id in enumerate(res["ids"][0]):
            out.append({
                "id": chunk_id,
                "text": res["documents"][0][i],
                "metadata": res["metadatas"][0][i],
                "distance": res["distances"][0][i] if res.get("distances") else None,
            })
        return out

    def list_by_lecture(self, lecture_id) -> list[dict]:
        res = self._collection().get(where={"lecture_id": lecture_id})
        rows = [
            {"id": cid, "text": doc, "metadata": meta}
            for cid, doc, meta in zip(res["ids"], res["documents"], res["metadatas"])
        ]
        return sorted(rows, key=lambda r: r["metadata"].get("order", 0))

    def update_text(self, chunk_id, text, embedding) -> None:
        self._collection().update(ids=[chunk_id], documents=[text], embeddings=[embedding])

    def delete_by_lecture(self, lecture_id) -> None:
        self._collection().delete(where={"lecture_id": lecture_id})


class LocalChromaVectors(_ChromaBase):
    """On-disk Chroma at CHROMA_DIR (the default dev backend)."""

    def _client(self):
        import chromadb
        return chromadb.PersistentClient(path=get_settings().chroma_dir)


class RemoteChromaVectors(_ChromaBase):
    """A hosted/remote Chroma server reached over HTTP (CHROMA_HTTP_URL)."""

    def _client(self):
        import chromadb

        s = get_settings()
        u = urlparse(s.chroma_http_url)
        ssl = u.scheme == "https"
        port = u.port or (443 if ssl else 80)
        headers = {"Authorization": f"Bearer {s.chroma_api_key}"} if s.chroma_api_key else None
        return chromadb.HttpClient(host=u.hostname, port=port, ssl=ssl, headers=headers)
