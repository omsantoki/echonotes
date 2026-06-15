"""Backfill vision diagram descriptions for already-processed lectures (T030 / FR-9 / US-5).

Earlier lectures were processed before a vision model was available, so every DiagramAsset
has description=null and the diagram chunks carry only a plain caption. This script runs the
vision model over each described-less diagram image and:

  1. stores the description on the DiagramAsset (registry), and
  2. updates the diagram NoteChunk's text + embedding in Chroma, so the description becomes
     the rendered caption AND is indexed for cross-lecture search.

Idempotent (only fills missing descriptions) and best-effort (skips on any failure). Requires
the configured vision model to be available (local: `ollama pull llava`).

Run:  python scripts/backfill_diagram_descriptions.py
"""

from __future__ import annotations

import pathlib
import sys

ROOT = str(pathlib.Path(__file__).resolve().parent.parent)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import diagrams, store          # noqa: E402
from app.embed import embed_text         # noqa: E402
from app.models import DiagramAsset      # noqa: E402


def main() -> int:
    # Backend-agnostic: works on the local JSON+disk store or the cloud
    # Postgres+object-storage backends, all via the public store API.
    assets = store.list_all_diagrams()
    todo = [a for a in assets if not a.get("description")]
    print(f"{len(assets)} diagram(s) total · {len(todo)} missing a description")
    if not todo:
        print("Nothing to backfill.")
        return 0

    updated = 0
    for a in todo:
        aid = a.get("id", "")
        image_ref = a.get("image_ref", "")
        data = store.read_diagram_bytes(a)
        if not data:
            print(f"  skip {aid}: image not found ({image_ref})")
            continue
        ext = image_ref.rsplit(".", 1)[-1] if "." in image_ref else "png"
        desc = diagrams.describe_image(data, ext, a.get("section_topic", "Diagram"))
        if not desc:
            print(f"  skip {aid}: vision model returned no description (model available?)")
            continue

        # 1) store on the DiagramAsset (registry), preserving its id
        store.create_diagram(DiagramAsset(**{**a, "description": desc}))

        # 2) make it the searchable text + caption on the diagram chunk
        for ch in store.list_chunks(a.get("lecture_id", "")):
            m = ch["metadata"]
            if m.get("source_type") == "diagram" and m.get("diagram_ref") == aid:
                store.update_chunk_text(ch["id"], desc, embed_text(desc))
                break

        updated += 1
        print(f"  described {aid}: {desc[:90]}{'…' if len(desc) > 90 else ''}")

    print(f"\nBackfilled {updated} diagram description(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
