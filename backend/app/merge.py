"""Merge composition (task T016): the heart of EchoNotes.

For each topic, an LLM synthesizes the UNION of the written SLIDE text and the SPOKEN
transcript into one clean, de-duplicated, reconstructed explanation: it keeps every
distinct point from either source, includes shared points exactly once, and rewrites
the combined material in its own words (never copying fragments or inventing facts —
Art. II, decision D-4). The notes are emitted as an ordered list of segments, each
labeled by source (slides | spoken) with a one-line reason (Art. II, III); points that
came only from the speech are flagged `spoken_only` so the UI emphasizes them inline
(FR-7, US-2). Because this pass already unifies + de-duplicates, the separate refine
pass is optional and off by default. Diagram segments are placed by the pipeline (T017).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache

from openai import OpenAI

from app.align import SectionAlignment
from app.config import get_settings, require_openai_key

_SYSTEM = (
    "You are a study-notes synthesizer for ONE lecture topic. You are given two sources "
    "that cover the SAME topic:\n"
    "  1. SLIDES — the text written on the slides / PDF.\n"
    "  2. TRANSCRIPT — what the professor actually said aloud.\n"
    "Produce ONE clean set of notes that is the UNION of both sources:\n"
    "• COMPLETENESS (keep everything): include every distinct fact, definition, example, "
    "number, formula, step, and caveat that appears in EITHER source. Drop nothing — if "
    "it's in the slides or in the speech, it must survive.\n"
    "• DEDUPLICATION (no repeats): when the same point appears in both sources (the "
    "professor restating a slide), include it exactly ONCE; merge the two versions into a "
    "single, clearest statement. Never say the same thing twice.\n"
    "• RECONSTRUCTION (rewrite, don't stitch): do NOT copy fragments verbatim or paste "
    "slide text next to transcript text. Re-express the combined material in clean, "
    "coherent, well-ordered prose, in your own words, as one continuous explanation. Fix "
    "grammar, ordering, and flow.\n"
    "• CLEAN: remove filler and transcription noise (ums, false starts, repetition); never "
    "write meta-phrases like 'the slide says' or 'the professor said'.\n"
    "• FAITHFUL: use ONLY what is in the two sources; never add outside facts or invent.\n"
    "Mental model: OUTPUT = clean_rewrite( union(slide_facts, spoken_facts) ).\n"
    "\n"
    "Then split your notes into an ORDERED list of segments (a sentence or two each) and "
    "LABEL each one — the labels carry provenance and do NOT appear in the prose:\n"
    "  - source_type: 'slides' if the point appears on the slide, otherwise 'spoken'.\n"
    "  - spoken_only: true if the point came ONLY from the transcript (not on the slide).\n"
    "  - reason: a short why.\n"
    "Use **bold** for key terms; start a segment's text with '- ' to make it a bullet.\n"
    'Respond as JSON: {"segments": [{"source_type": "slides"|"spoken", "text": string, '
    '"reason": string, "spoken_only": boolean}]}'
)


@dataclass
class Block:
    source_type: str    # "slides" | "spoken"
    text: str
    reason: str
    confidence: float
    spoken_only: bool = False


@lru_cache
def _client() -> OpenAI:
    s = get_settings()
    if s.provider == "local":
        # Ollama exposes an OpenAI-compatible API; the key is required by the SDK
        # but ignored by Ollama.
        return OpenAI(base_url=s.ollama_base_url.rstrip("/") + "/v1", api_key="ollama")
    return OpenAI(api_key=require_openai_key())


def _model() -> str:
    s = get_settings()
    return s.ollama_model if s.provider == "local" else s.chat_model


def merge_section(sa: SectionAlignment) -> list[Block]:
    """Compose the note blocks for one slide section + its aligned speech."""
    slide_text = sa.section.text.strip()
    spoken = " ".join(seg.text for seg in sa.spoken).strip()
    spoken_conf = (
        sum(seg.score for seg in sa.spoken) / len(sa.spoken) if sa.spoken else 0.0
    )

    if not slide_text and not spoken:
        return []

    user = json.dumps(
        {"topic": sa.section.title, "SLIDES": slide_text, "TRANSCRIPT": spoken},
        ensure_ascii=False,
    )

    try:
        resp = _client().chat.completions.create(
            model=_model(),
            response_format={"type": "json_object"},
            temperature=0.2,
            messages=[{"role": "system", "content": _SYSTEM},
                      {"role": "user", "content": user}],
        )
        segments = _parse_segments(json.loads(resp.choices[0].message.content), spoken_conf)
        if segments:
            return segments
    except Exception:
        pass  # never lose content if the LLM call / formatting fails

    return _fallback_segments(slide_text, spoken, spoken_conf)


def _parse_segments(data: dict, spoken_conf: float) -> list[Block]:
    out: list[Block] = []
    for b in data.get("segments", []):
        st = b.get("source_type")
        text = (b.get("text") or "").strip()
        if st not in ("slides", "spoken") or not text:
            continue
        reason = (b.get("reason") or "").strip() or (
            "From the slides." if st == "slides" else "Said in the lecture."
        )
        out.append(Block(
            source_type=st,
            text=text,
            reason=reason,
            confidence=1.0 if st == "slides" else round(spoken_conf, 3),
            spoken_only=bool(b.get("spoken_only")) and st == "spoken",
        ))
    return out


def _fallback_segments(slide_text: str, spoken: str, spoken_conf: float) -> list[Block]:
    out: list[Block] = []
    if slide_text:
        out.append(Block("slides", slide_text, "Extracted directly from the slide.", 1.0))
    if spoken:
        out.append(Block("spoken", spoken,
                         "Transcribed from the professor's explanation.",
                         round(spoken_conf, 3), spoken_only=True))
    return out
