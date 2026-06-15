"""Alignment (task T015): match spoken segments to slide sections.

Uses the ONE embedding model (Art. VI, via embed.py) to embed slide-section text
and transcript segments, then attaches each spoken segment to its best-matching
slide sections by cosine similarity — top-k (default 3, `align_top_k`; decision D-1).
The best match is always kept; near-tie runner-ups are added too, so an explanation
that spans slides reaches each relevant section instead of being forced into one and
losing context. Every match carries an alignment confidence and a reason (Art. II).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from app.config import get_settings
from app.embed import embed_texts
from app.slides import SlideSection
from app.transcribe import Segment

# A runner-up section is only attached if it is at least this fraction as similar
# as the best match — keeps clearly-single segments from scattering across slides.
_NEAR_TIE = 0.85


@dataclass
class AlignedSegment:
    text: str
    start: float
    end: float
    score: float    # alignment confidence in [0, 1]
    reason: str


@dataclass
class SectionAlignment:
    section: SlideSection
    spoken: list[AlignedSegment] = field(default_factory=list)


def align(sections: list[SlideSection], segments: list[Segment]) -> list[SectionAlignment]:
    """Group spoken segments under the slide section each best corresponds to."""
    result = [SectionAlignment(section=s) for s in sections]
    if not sections or not segments:
        return result

    section_texts = [f"{s.title}\n{s.text}".strip() for s in sections]
    seg_texts = [seg.text for seg in segments]

    sec_vecs = _unit(np.asarray(embed_texts(section_texts), dtype=float))
    seg_vecs = _unit(np.asarray(embed_texts(seg_texts), dtype=float))

    sims = seg_vecs @ sec_vecs.T  # (n_segments, n_sections) cosine similarities

    k = max(1, get_settings().align_top_k)
    n = len(sections)
    for si, seg in enumerate(segments):
        ranked = np.argsort(sims[si])[::-1]          # section indices, best first
        best_score = float(np.clip(sims[si][ranked[0]], 0.0, 1.0))
        for rank, sec_i in enumerate(ranked[:k]):
            score = float(np.clip(sims[si][sec_i], 0.0, 1.0))
            # always keep the best; attach runner-ups only when genuinely close
            if rank > 0 and score < _NEAR_TIE * best_score:
                break
            reason = (
                f"Matched to “{sections[int(sec_i)].title}” by semantic similarity "
                f"(score {score:.2f}); top-{rank + 1} of {n} slide sections."
            )
            result[int(sec_i)].spoken.append(AlignedSegment(
                text=seg.text, start=seg.start, end=seg.end, score=score, reason=reason,
            ))
    return result


def _unit(mat: np.ndarray) -> np.ndarray:
    if mat.size == 0:
        return mat
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return mat / norms
