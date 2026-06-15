"""Refinement pass (task T016, polish): a second LLM rewrites the merged segments
for a topic into ONE clean, de-duplicated, well-explained study narrative.

The professor often restates what's on the slide, so the raw merge can repeat itself.
This pass collapses those duplicates and improves the explanation. Provenance is kept
in the data (each output segment still carries `source_type`), so the constitution's
source labeling holds (Art. III) and **spoken-only** insights stay flagged + emphasized
— but the prose reads as a single unified explanation, not "this came from the slide,
this from speech". Best-effort: if the LLM/parsing fails, the merged segments pass
through unchanged.
"""

from __future__ import annotations

import json
from functools import lru_cache

from openai import OpenAI

from app.config import get_settings, require_openai_key
from app.merge import Block  # reuse the segment dataclass

_SYSTEM = (
    "You are EchoNotes' notes editor. You receive draft study notes for ONE topic as "
    "labeled segments (some from the slides, some said aloud, some spoken-only). Improve "
    "READABILITY WITHOUT LOSING INFORMATION.\n"
    "Rules:\n"
    "1. PRESERVE EVERY distinct fact, definition, example, number, formula, step and "
    "nuance. Do NOT summarize, condense, or omit anything.\n"
    "2. Only merge two segments when they state the SAME point in different words (a true "
    "duplicate — e.g. the slide and the professor saying the same thing). Never drop a "
    "unique detail just to be shorter.\n"
    "3. Improve flow, ordering and grammar; write it as ONE explanation — do NOT include "
    "phrases like 'the slide says' or 'the professor said'. Use **bold** for key terms "
    "and '- ' bullets where helpful.\n"
    "4. Keep provenance in the LABELS only: spoken_only=true (source_type 'spoken') for a "
    "point that came ONLY from what was said; source_type 'slides' otherwise.\n"
    "5. Use ONLY the provided material; never invent facts.\n"
    'Respond as JSON: {"segments": [{"source_type": "slides"|"spoken", "text": string, '
    '"reason": string, "spoken_only": boolean}]}'
)


@lru_cache
def _client() -> OpenAI:
    s = get_settings()
    if s.provider == "local":
        return OpenAI(base_url=s.ollama_base_url.rstrip("/") + "/v1", api_key="ollama")
    return OpenAI(api_key=require_openai_key())


def _model() -> str:
    s = get_settings()
    if s.refine_model:
        return s.refine_model
    return s.ollama_model if s.provider == "local" else s.chat_model


def refine_section(topic: str, segments: list[Block]) -> list[Block]:
    """Rewrite a topic's merged segments into a clean, de-duplicated narrative."""
    if not get_settings().refine_notes or not segments:
        return segments

    payload = {
        "topic": topic,
        "draft_segments": [
            {"source_type": b.source_type, "text": b.text, "spoken_only": b.spoken_only}
            for b in segments
        ],
    }
    try:
        resp = _client().chat.completions.create(
            model=_model(),
            response_format={"type": "json_object"},
            temperature=0.2,
            messages=[{"role": "system", "content": _SYSTEM},
                      {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
        )
        refined = _parse(json.loads(resp.choices[0].message.content), segments)
        if refined:
            return refined
    except Exception:
        pass  # best-effort polish — fall back to the un-refined merge

    return segments


def _parse(data: dict, original: list[Block]) -> list[Block]:
    spoken_conf = next((b.confidence for b in original if b.source_type == "spoken"), 0.8)
    out: list[Block] = []
    for s in data.get("segments", []):
        st = s.get("source_type")
        text = (s.get("text") or "").strip()
        if st not in ("slides", "spoken") or not text:
            continue
        reason = (s.get("reason") or "").strip() or "Refined, de-duplicated study note."
        out.append(Block(
            source_type=st,
            text=text,
            reason=reason,
            confidence=1.0 if st == "slides" else round(spoken_conf, 3),
            spoken_only=bool(s.get("spoken_only")) and st == "spoken",
        ))
    return out
