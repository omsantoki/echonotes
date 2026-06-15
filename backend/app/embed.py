"""The single embedding wrapper (task T006).

EVERY embedding in EchoNotes is produced here — alignment, storage, and search —
using ONE model/version (Constitution Art. VI). Do not embed anywhere else;
mixing embedding spaces breaks similarity comparisons.

Two providers, one active at a time (config.provider):
  * "local"  — sentence-transformers, on this machine, no API.
  * "openai" — OpenAI's embeddings endpoint.
Within a course every vector must come from the same provider+model.
"""

from __future__ import annotations

from functools import lru_cache

from app.config import get_settings, require_openai_key


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts with the one configured embedding model."""
    if not texts:
        return []
    if get_settings().provider == "local":
        # normalize_embeddings -> unit vectors, ideal for cosine similarity.
        return _local_model().encode(texts, normalize_embeddings=True).tolist()
    resp = _openai().embeddings.create(model=get_settings().embedding_model, input=texts)
    return [item.embedding for item in sorted(resp.data, key=lambda d: d.index)]


def embed_text(text: str) -> list[float]:
    """Embed a single string."""
    return embed_texts([text])[0]


@lru_cache
def _local_model():
    from sentence_transformers import SentenceTransformer
    # Downloaded + cached on first use (~90 MB for all-MiniLM-L6-v2).
    return SentenceTransformer(get_settings().local_embedding_model)


@lru_cache
def _openai():
    from openai import OpenAI
    return OpenAI(api_key=require_openai_key())
