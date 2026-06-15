# Quickstart: EchoNotes Core

<!-- Spec Kit artifact: specs/001-echonotes-core/quickstart.md -->

> Confirm current versions of all tools before installing (see research.md open tasks).

## Prerequisites
- Python 3.11+
- An LLM/vision API key and an embedding model (set in `.env`)
- ffmpeg (for audio handling by the transcription step)

## Setup
```bash
git clone <repo> && cd echonotes
git checkout 001-echonotes-core
python -m venv .venv && source .venv/bin/activate
cd backend                             # the FastAPI backend lives here
pip install -r requirements.txt        # fastapi, uvicorn, pymupdf, chromadb, whisper/STT client, llm client, etc.
cp .env.example .env                   # fill in keys
```

## Run locally
```bash
# from backend/
uvicorn app.main:app --reload
# open http://localhost:8000
```

## Process the demo lecture (validation gate T022)
1. Create a course in the UI (or `POST /api/courses`).
2. Upload the demo lecture's audio + slides PDF.
3. Watch progress; when ready, open the merged document.
4. Confirm: flowing woven notes per topic, inline source labels, a visibly highlighted spoken-only capture, diagrams in place.

## Show continuity (demo)
- Process 2–3 lectures of the same course in sequence.
- Open the later lecture; confirm prior-context framing / links (Stretch) and that search spans all of them (Strong).

## Deploy (T050)
- Backend → Render/Railway (Python). Frontend → same host or Vercel if split.
- Set environment variables (keys) in the host dashboard.
- Verify the public URL processes a lecture end-to-end.

## Privacy check (Art. IV)
- After processing, confirm no raw audio remains in storage — only NoteChunks and DiagramAssets.
