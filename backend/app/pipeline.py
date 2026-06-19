"""Pipeline orchestration (Core merge — tasks T010, T015–T018).

Runs in the background after POST /api/lectures returns 202. Sequence:
transcribe -> extract slides (text + images, filtered) -> align -> merge ->
refine (dedupe + clean explanation) -> place diagrams (T017) -> embed ->
persist per course (T018). Progress is written to the lecture for the polling UI.

Raw audio is deleted the moment transcription finishes, and the entire temp
workspace is removed in `finally` — so no recording ever survives, even on
failure (Constitution Art. IV).
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from app import cache, diagrams, refine, retrieve, store
from app.align import align
from app.embed import embed_texts
from app.merge import merge_section
from app.models import DiagramAsset, LectureStatus, NoteChunk, SourceType
from app.slides import extract_slides, filter_images
from app.transcribe import transcribe

# Errors worth retrying (network blips to STT / the LLM / the vector store or registry).
# These propagate so Celery can retry the task; everything else is treated as a permanent
# failure and recorded on the lecture. Kept conservative on purpose.
_TRANSIENT = (ConnectionError, TimeoutError)


class _InputsMissing(RuntimeError):
    """The stored uploads could not be read — a permanent failure for this lecture."""


def run_pipeline(lecture_id: str, course_id: str, audio_name: str,
                 pdf_name: str) -> None:
    """Process one lecture. Safe to re-run (idempotent): a redelivered task for an
    already-finished lecture is a no-op, and a re-run after a crash clears partial
    output first. Raw audio never survives the run (Art. IV)."""
    # Idempotency: skip if the lecture was deleted, or already finished by an earlier
    # delivery of this same task (acks_late can re-deliver after a successful run).
    lec = store.get_lecture(lecture_id)
    if not lec or lec.get("status") == LectureStatus.ready.value:
        return

    workdir = Path(tempfile.mkdtemp(prefix="echonotes_"))
    try:
        _process(lecture_id, course_id, audio_name, pdf_name, workdir)

        # New notes just landed — clear the course's Q&A cache so cached answers can't
        # mask the new content (no-op when no Redis is configured).
        cache.invalidate(course_id)
        store.update_lecture(lecture_id, status=LectureStatus.ready, progress="Ready.")
        store.delete_uploads(lecture_id)  # success → no audio survives (Art. IV)
    except _TRANSIENT as exc:
        # Leave status=processing and KEEP the stored uploads so the retry can re-read
        # them; re-raise so Celery retries the task with backoff.
        store.update_lecture(lecture_id, progress=f"Temporary error, retrying… ({exc})")
        raise
    except Exception as exc:  # permanent failure — record it; never crash the worker
        store.update_lecture(lecture_id, status=LectureStatus.failed,
                             progress=f"Failed: {exc}")
        store.delete_uploads(lecture_id)  # permanent failure → no audio survives (Art. IV)
    finally:
        # The local working copy is always removed; the shared upload is removed on every
        # terminal outcome here (and on retry exhaustion by the task's on_failure).
        shutil.rmtree(workdir, ignore_errors=True)


def _process(lecture_id: str, course_id: str, audio_name: str,
             pdf_name: str, workdir: Path) -> None:
    """The pipeline body. Raises on failure (transient errors bubble up for retry)."""
    audio_path = workdir / audio_name
    pdf_path = workdir / pdf_name
    if not store.read_upload(lecture_id, audio_name, str(audio_path)) or \
            not store.read_upload(lecture_id, pdf_name, str(pdf_path)):
        raise _InputsMissing("Uploaded audio/slides are no longer available.")

    # Re-run hygiene: a redelivery after a mid-run crash starts from a clean slate so
    # chunks/diagrams aren't duplicated (no-op on a first run).
    store.reset_lecture_artifacts(lecture_id)

    store.update_lecture(lecture_id, status=LectureStatus.processing,
                         progress="Transcribing audio…")
    segments = transcribe(str(audio_path))
    _safe_delete(str(audio_path))  # local audio's job is done — delete now (Art. IV)

    store.update_lecture(lecture_id, progress="Reading slides…")
    sections, images = extract_slides(str(pdf_path))
    images = filter_images(images, num_pages=len(sections))

    store.update_lecture(lecture_id, progress="Aligning what was said to the slides…")
    aligned = align(sections, segments)

    store.update_lecture(lecture_id, progress="Describing diagrams…")
    diagrams_by_section = _persist_diagrams(lecture_id, sections, images)

    store.update_lecture(lecture_id, progress="Composing your merged notes…")
    chunks = _compose_chunks(lecture_id, course_id, aligned, diagrams_by_section)
    if not chunks:
        raise RuntimeError("No content was produced from the audio + slides.")

    store.update_lecture(lecture_id, progress="Saving notes…")
    for chunk, vector in zip(chunks, embed_texts([c.text for c in chunks])):
        chunk.embedding = vector
    store.add_chunks(chunks)
    _link_prior_lectures(lecture_id, course_id, chunks)


def _compose_chunks(lecture_id, course_id, aligned, diagrams_by_section) -> list[NoteChunk]:
    chunks: list[NoteChunk] = []
    order = 0
    for sa in aligned:
        # merge weaves slide + spoken; refine then de-duplicates + cleans the prose
        # into one explanation (provenance preserved, spoken-only still flagged).
        segments = refine.refine_section(sa.section.title, merge_section(sa))
        for b in segments:
            reason = b.reason
            if b.spoken_only:
                reason = "★ Spoken-only (not on the slides) — " + reason
            chunks.append(NoteChunk(
                lecture_id=lecture_id, course_id=course_id, topic=sa.section.title,
                order=order, text=b.text, source_type=SourceType(b.source_type),
                reason=reason, confidence=b.confidence,
            ))
            order += 1
        for asset in diagrams_by_section.get(sa.section.index, []):
            # description (Strong, T030) doubles as the searchable text + caption;
            # falls back to a plain caption when no vision model is available.
            caption = asset.description or f"Diagram from “{sa.section.title}”."
            reason = "Preserved from this slide section (US-3)."
            if asset.description:
                reason += " Description generated by a vision model (US-5)."
            chunks.append(NoteChunk(
                lecture_id=lecture_id, course_id=course_id, topic=sa.section.title,
                order=order, text=caption,
                source_type=SourceType.diagram, reason=reason,
                confidence=1.0, diagram_ref=asset.id,
            ))
            order += 1
    return chunks


def _link_prior_lectures(lecture_id: str, course_id: str, chunks: list[NoteChunk]) -> None:
    """Stretch (T040/T041): link each topic to the most similar earlier lecture.

    Best-effort — linking never fails the pipeline. Uses each topic's combined text to
    find the strongest prior match (capped, similarity-thresholded; Art. VI), excluding
    this lecture so it never links to itself.
    """
    try:
        topic_texts: dict[str, list[str]] = {}
        for c in chunks:
            if c.source_type != SourceType.diagram and c.text.strip():
                topic_texts.setdefault(c.topic, []).append(c.text)
        links = retrieve.find_links(
            course_id,
            [(t, " ".join(v)) for t, v in topic_texts.items()],
            exclude_lecture_id=lecture_id,
        )
        if links:
            store.set_lecture_links(lecture_id, links)
    except Exception:
        pass


def _persist_diagrams(lecture_id, sections, images) -> dict[int, list[DiagramAsset]]:
    out: dict[int, list[DiagramAsset]] = {}
    for im in images:
        topic = sections[im.section_index].title if im.section_index < len(sections) else "Diagram"
        asset = DiagramAsset(lecture_id=lecture_id, image_ref="", section_topic=topic)
        asset.image_ref = store.save_diagram_image(lecture_id, asset.id, im.ext, im.data)
        asset.description = diagrams.describe_image(im.data, im.ext, topic)  # Strong (T030)
        store.create_diagram(asset)
        out.setdefault(im.section_index, []).append(asset)
    return out


def _safe_delete(path: str) -> None:
    try:
        Path(path).unlink(missing_ok=True)
    except OSError:
        pass
