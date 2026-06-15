"""Slide extraction + image filtering (tasks T012, T013, T014).

PyMuPDF turns a slides PDF into ordered sections (one per page) with their text,
and pulls embedded images tagged with the section they came from. Decorative /
template images — logos, repeated banners, tiny bullets/icons — are filtered out
(FR-4) so only meaningful diagrams reach the merged document.
"""

from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import dataclass

import fitz  # PyMuPDF


@dataclass
class SlideSection:
    index: int       # 0-based page / section order
    title: str
    text: str


@dataclass
class SlideImage:
    section_index: int
    data: bytes
    ext: str
    width: int
    height: int
    sha1: str


_MIN_DIM = 100              # px — below this is an icon/bullet, not a diagram
_MIN_AREA = 100 * 100       # px^2


def extract_slides(pdf_path: str) -> tuple[list[SlideSection], list[SlideImage]]:
    """Extract ordered text sections and embedded images from a slides PDF."""
    doc = fitz.open(pdf_path)
    try:
        sections = [_section(i, page) for i, page in enumerate(doc)]
        images = _images(doc)
    finally:
        doc.close()
    return sections, images


def _section(index: int, page) -> SlideSection:
    text = page.get_text("text").strip()
    return SlideSection(index=index, title=_first_line(text) or f"Slide {index + 1}",
                        text=text)


def _first_line(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line:
            return line[:120]
    return ""


def _images(doc) -> list[SlideImage]:
    out: list[SlideImage] = []
    for i, page in enumerate(doc):
        for img in page.get_images(full=True):
            xref = img[0]
            try:
                info = doc.extract_image(xref)
            except Exception:
                continue
            data = info.get("image")
            if not data:
                continue
            out.append(SlideImage(
                section_index=i,
                data=data,
                ext=info.get("ext", "png"),
                width=int(info.get("width", 0)),
                height=int(info.get("height", 0)),
                sha1=hashlib.sha1(data).hexdigest(),
            ))
    return out


def filter_images(images: list[SlideImage], num_pages: int) -> list[SlideImage]:
    """Drop tiny, repeated, and template images (FR-4)."""
    if not images:
        return []
    counts = Counter(im.sha1 for im in images)
    # An image on ~a third or more of the slides is a logo/banner, not content.
    repeat_threshold = max(2, int(0.3 * max(num_pages, 1)))
    kept: list[SlideImage] = []
    seen: set[str] = set()
    for im in images:
        if im.width < _MIN_DIM or im.height < _MIN_DIM:
            continue
        if im.width * im.height < _MIN_AREA:
            continue
        if counts[im.sha1] >= repeat_threshold:
            continue
        if im.sha1 in seen:        # exact duplicate already kept
            continue
        seen.add(im.sha1)
        kept.append(im)
    return kept
