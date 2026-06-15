
"""T022 validation gate — run the FULL pipeline on the demo lecture and check the
acceptance criteria on real data (Art. VIII).

Runs ingest→transcribe→slides→align→describe→merge→store→link end-to-end on the
samples/ demo lecture in a THROWAWAY store (does not touch your real ./data or ./.chroma),
then asserts:

  * the lecture reaches status=ready,
  * the temp audio workspace is deleted (Art. IV),
  * the document is topic-organized with source labels,
  * at least one SPOKEN-ONLY item is captured (the "wow"),
  * diagrams are preserved in place, and described by the vision model (T030),

and prints the rendered notes so a human can confirm they "read like real study notes."

Requires Ollama running (`llama3.1` for merge, `llava` for diagram descriptions) and the
local transcription/embedding stack. Run:

    python scripts/validate_demo.py
"""

from __future__ import annotations

import os
import pathlib
import shutil
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "samples"

# Isolated throwaway store so a validation run never pollutes real data.
_TMP = tempfile.mkdtemp(prefix="echonotes_validate_")
os.environ["DATA_DIR"] = str(pathlib.Path(_TMP) / "data")
os.environ["CHROMA_DIR"] = str(pathlib.Path(_TMP) / "chroma")
os.environ.setdefault("PROVIDER", "local")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import pipeline, render, store          # noqa: E402
from app.models import Course, Lecture, LectureStatus  # noqa: E402


def _pick_audio() -> pathlib.Path | None:
    for p in sorted(SAMPLES.iterdir()):
        if p.suffix.lower() in {".mp3", ".wav", ".m4a", ".m4b", ".ogg", ".flac"}:
            return p
    return None


def main() -> int:
    pdf = SAMPLES / "Photosynthesis_Notes.pdf"
    audio = _pick_audio()
    if not pdf.exists() or not audio:
        print(f"FAIL — need a PDF + an audio file in {SAMPLES}")
        return 1
    print(f"Demo lecture: slides={pdf.name}  audio={audio.name}")

    course = store.create_course(Course(name="Validation — Photosynthesis"))
    lec = Lecture(course_id=course.id, title="Demo lecture", status=LectureStatus.processing)
    store.create_lecture(lec)
    lecture_id = lec.id

    work = pathlib.Path(tempfile.mkdtemp())
    audio_path = work / ("audio" + audio.suffix)
    shutil.copy(audio, audio_path)
    shutil.copy(pdf, work / "slides.pdf")

    print("Running full pipeline (transcribe → slides → align → describe → merge → store)…")
    print("This is heavy: real transcription + one LLM call per topic + vision per diagram.\n")
    pipeline.run_pipeline(lecture_id, course.id, str(audio_path), str(work / "slides.pdf"), str(work))

    lec = store.get_lecture(lecture_id)
    doc = store.assemble_document(lecture_id)
    segs = [s for t in doc["topics"] for s in t["segments"]]
    spoken_only = [s for s in segs if s.get("spoken_only")]
    diagrams = [s for s in segs if s.get("source_type") == "diagram"]
    described = [s for s in diagrams if s.get("text") and not s["text"].startswith("Diagram from")]
    audio_survived = audio_path.exists() or work.exists()

    ok = True
    def check(name: str, cond: bool) -> None:
        nonlocal ok
        ok = ok and cond
        print(("PASS" if cond else "FAIL"), "-", name)

    print("\n=== T022 / T030 — acceptance criteria on the real demo lecture ===")
    check("lecture reached status=ready", lec["status"] == "ready")
    check("temp audio workspace deleted (Art. IV)", not audio_survived)
    check("document is topic-organized", len(doc["topics"]) >= 1)
    check("source labels present (>=2 of slides/spoken/diagram)",
          len({s["source_type"] for s in segs}) >= 2)
    check("at least one SPOKEN-ONLY item captured", len(spoken_only) >= 1)
    check("diagram(s) preserved in place", len(diagrams) >= 1)
    check("diagram(s) described by vision model (T030)", len(described) >= 1)
    if lec["status"] != "ready":
        print("  progress:", lec.get("progress"))

    print(f"\nTopics: {len(doc['topics'])} | segments: {len(segs)} | "
          f"spoken-only: {len(spoken_only)} | diagrams: {len(diagrams)} (described: {len(described)})")
    if spoken_only:
        print("\n----- example SPOKEN-ONLY capture (said, not on slides) -----")
        print(" ", spoken_only[0]["text"])
    if described:
        print("\n----- example DIAGRAM description (vision) -----")
        print(" ", described[0]["text"])

    print("\n========== RENDERED NOTES (read these like study notes) ==========\n")
    print(render.document_to_markdown("Demo lecture", doc))

    shutil.rmtree(_TMP, ignore_errors=True)
    print("\nRESULT:", "PASS — demo lecture validated" if ok else "FAIL — see checks above")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
