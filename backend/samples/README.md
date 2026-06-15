# backend/samples/ — the demo lecture (task T005, Day-1 critical)

This folder holds the **demo lecture** that gates the whole project: the T022 validation
gate runs the full pipeline on it, and Article VIII says "a feature that cannot be shown
working on real data does not count as done."

## What's here now

```
backend/samples/
├── Photosynthesis_Notes.pdf                      # the slide/notes deck (committed)
├── Record (online-voice-recorder.com).mp3        # lecture audio (local only, git-ignored)
├── Record (online-voice-recorder.com)-2.mp3      # a 2nd lecture's audio (local only)
└── README.md
```

The **PDF is committed**; the **audio is intentionally git-ignored** (`.gitignore` excludes
`backend/samples/*.mp3|*.wav|*.m4a`) because raw audio is never committed or persisted (Art. IV).
These are real, self-recorded clips — usable, though clean audio remains the top demo risk
(spec §9); swap in a clearer recording for the best result.

## How it's used

- **Validate (T022):** from `backend/`, `python scripts/validate_demo.py` runs the full pipeline on
  this lecture in a throwaway store and checks the gate criteria (topics, source labels, a
  captured spoken-only item, diagrams in place + described). Requires Ollama running
  (`llama3.1` for merge, `llava` for diagram descriptions).
- **Use the app:** from `backend/`, start `uvicorn app.main:app --reload`, create a course at `/`, and upload
  `Photosynthesis_Notes.pdf` + one of the `.mp3` files.

## Continuity demo (Strong + Stretch)

Process 2–3 lectures of the **same course** in sequence so search (T031) and cross-lecture
"builds on" links (T041) have material. The local store already has a Biology course with
three processed lectures demonstrating this.

## Rules

- **Clean audio is the top demo risk** (spec §9) — pick the clearest recording; self-record if needed.
- **PDF slides only** for the event (research.md scope decision).
- **Raw audio is never persisted by the app** (Art. IV): the pipeline deletes its temp copy
  right after transcription, and the whole temp workspace is removed even on failure.
