"""Diagram description via a vision model (task T030, FR-9 — Strong).

For each meaningful slide diagram, a vision-capable model writes a short description
so the diagram is explained in the notes and indexed for search (US-5). Provider-aware:
a local Ollama vision model (e.g. llava) or OpenAI's multimodal chat model.

Best-effort by design: if no vision model is available or the call fails, returns None
and the pipeline keeps the diagram with a plain caption (Core behavior is unchanged).
Honors the constitution's "no deep diagram parsing" boundary (Art. VII) — it conveys
the concept, it does not extract every value.
"""

from __future__ import annotations

import base64
from functools import lru_cache

from openai import OpenAI

from app.config import get_settings, require_openai_key

_PROMPT = (
    "This is a diagram from a lecture slide on the topic “{topic}”. In 1-3 sentences, "
    "describe for a student what it shows and the key relationship or idea it conveys. "
    "Capture the concept, not every label; never invent values. If it is decorative "
    "(a logo, photo, or has no instructional content), reply with exactly: SKIP"
)


@lru_cache
def _client() -> OpenAI:
    s = get_settings()
    if s.provider == "local":
        return OpenAI(base_url=s.ollama_base_url.rstrip("/") + "/v1", api_key="ollama")
    return OpenAI(api_key=require_openai_key())


def _model() -> str:
    s = get_settings()
    return s.ollama_vision_model if s.provider == "local" else s.chat_model


def describe_image(image_bytes: bytes, ext: str, topic: str) -> str | None:
    """Return a concise description of a diagram image, or None (best-effort)."""
    if not get_settings().describe_diagrams or not image_bytes:
        return None
    ext = (ext or "png").lstrip(".")
    data_url = f"data:image/{ext};base64,{base64.b64encode(image_bytes).decode()}"
    try:
        resp = _client().chat.completions.create(
            model=_model(),
            temperature=0.2,
            messages=[{"role": "user", "content": [
                {"type": "text", "text": _PROMPT.format(topic=topic)},
                {"type": "image_url", "image_url": {"url": data_url}},
            ]}],
        )
        text = (resp.choices[0].message.content or "").strip()
        if not text or text.upper().startswith("SKIP"):
            return None
        return text
    except Exception:
        return None  # no vision model / call failed → keep the diagram, no description
