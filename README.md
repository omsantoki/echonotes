# EchoNotes

> Merges a lecture's **audio** (what was said) with its **slides** (what was written) into one
> **source-labeled, topic-organized** study document — and remembers notes **per course** so lectures
> build on each other.

<p>
  <img alt="Python" src="https://img.shields.io/badge/python-3.11-blue?logo=python&logoColor=white" />
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-0.136-009688?logo=fastapi&logoColor=white" />
  <img alt="React" src="https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black" />
  <img alt="Supabase" src="https://img.shields.io/badge/Supabase-3ECF8E?logo=supabase&logoColor=white" />
  <img alt="Qdrant" src="https://img.shields.io/badge/Qdrant-DC244C?logo=qdrant&logoColor=white" />
  <img alt="AWS S3" src="https://img.shields.io/badge/AWS%20S3-569A31?logo=amazons3&logoColor=white" />
  <img alt="Deploy" src="https://img.shields.io/badge/deploy-Render%20%2B%20Vercel-46E3B7" />
  <img alt="License" src="https://img.shields.io/badge/license-TODO-lightgrey" /> <!-- TODO: confirm -->
</p>

**🔴 Live demo: [echonotes-sooty.vercel.app](https://echonotes-sooty.vercel.app)**

An **AI-powered, RAG-based full-stack web app** — a multimodal pipeline combining **speech-to-text**,
**document/PDF parsing**, **vision LLMs**, **text embeddings**, and **vector search** behind a FastAPI
backend and a React SPA.

## Why

Slides-only notes lose the professor's spoken asides ("this *will* be on the exam"). Transcript-only
notes lose the deck's structure, wording, and diagrams. EchoNotes **merges both** and labels every
block by where it came from — so the highest-value, most-easily-lost content (spoken-only insight)
survives.

Every block is tagged `slides` / `spoken` / `diagram`, carries a plain-language `reason` (it shows its
work — not a chatbot wrapper), and **spoken-only** content is emphasized. **Raw audio is never
persisted** — it's deleted right after transcription.

## How it works

```
ingest → transcribe → (🗑️ delete audio) → slides → align → diagrams → merge → embed → store → retrieve → api → web
```

Audio is transcribed then deleted; slide text + images are extracted (decorative images filtered);
spoken segments are **aligned** to slide sections via cosine similarity using **one embedding model**;
merge weaves them into a labeled narrative; chunks are embedded and persisted **per course** (so search
and cross-lecture "builds on" links work).

## Tech stack

| Layer | Technology |
|---|---|
| **Backend / API** | Python 3.11, FastAPI, Uvicorn, Pydantic + pydantic-settings |
| **Speech-to-text** | OpenAI Whisper (`whisper-1`) / `faster-whisper` (on-device) |
| **PDF parsing** | PyMuPDF (text + embedded image extraction) |
| **Embeddings** | one model — `sentence-transformers` (`all-MiniLM-L6-v2`) or OpenAI `text-embedding-3-small` |
| **LLMs** | Ollama (`llama3.1`) / OpenAI (`gpt-4o`) for merge; vision LLM (`llava` / `gpt-4o`) for diagrams |
| **Vector store** | Chroma (local) → **Qdrant Cloud** (prod) |
| **Registry / DB** | JSON file (local) → **Supabase** (managed Postgres) via `psycopg` (prod) |
| **Object storage** | local `/assets` (dev) → **AWS S3** via `boto3` (prod) |
| **Numerics** | NumPy (cosine similarity for alignment) |
| **Frontend** | React 19, Vite, TypeScript, Tailwind CSS, TanStack Query, React Router |
| **Deploy** | Render / Railway (backend, Docker) · Vercel (frontend) |

## Quick start

> Run all backend commands from `backend/`.

```bash
# backend
cd backend
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt              # + requirements-local.txt for the on-device default
cp .env.example .env                          # PROVIDER=local (Ollama) or PROVIDER=openai + OPENAI_API_KEY
uvicorn app.main:app --reload                 # http://localhost:8000  (docs at /docs)

# frontend (new shell)
cd frontend && npm install && npm run dev     # http://localhost:5173
```

Validate on the demo lecture: `cd backend && python scripts/validate_demo.py`
(`Photosynthesis_Notes.pdf` is in [`backend/samples/`](backend/samples/); audio is git-ignored).

## API

Base `/api` · errors are `{"error": {"code", "message"}}`. Full contract:
[`specs/001-echonotes-core/contracts/api.md`](specs/001-echonotes-core/contracts/api.md).

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/courses` | Create a course `{name}` |
| `GET` | `/api/courses` · `/api/courses/{id}` | List / detail |
| `GET` | `/api/courses/{id}/search?q=` | Cross-lecture semantic search |
| `POST` | `/api/lectures` | Upload (multipart: `course_id`, `title`, `audio`, `slides`) → `202 processing` |
| `GET` | `/api/lectures/{id}` | Poll status / get merged `document` |
| `GET` | `/api/lectures/{id}/export?format=md\|html` | Download notes |
| `DELETE` | `/api/lectures/{id}` · `/api/courses/{id}` | Delete (cascades) |
| `GET` | `/api/health` | Liveness + active provider/storage |

<details>
<summary>Ready document shape</summary>

```json
{ "id": "...", "status": "ready", "title": "...",
  "document": { "topics": [ {
    "topic": "The Calvin Cycle",
    "segments": [
      { "source_type": "slides", "text": "...", "reason": "...", "spoken_only": false },
      { "source_type": "spoken", "text": "...", "reason": "★ Spoken-only — matched by similarity (0.81)", "spoken_only": true },
      { "source_type": "diagram", "text": "caption", "reason": "...", "image_ref": "/assets/{lec}/{id}.png" }
    ],
    "builds_on": { "lecture_title": "Week 2", "topic": "Light Reactions", "similarity": 0.74 }
  } ] } }
```
</details>

## Configuration

Set in `backend/.env` (see [`.env.example`](backend/.env.example)). Leave managed-storage vars blank for
local dev — each subsystem switches to its managed service when its var is set.

| Var | Default | Notes |
|---|---|---|
| `PROVIDER` | `local` | `local` (Ollama + faster-whisper, no keys) or `openai` |
| `OPENAI_API_KEY` | — | required when `PROVIDER=openai` |
| `EMBEDDING_MODEL` / `LOCAL_EMBEDDING_MODEL` | `text-embedding-3-small` / `all-MiniLM-L6-v2` | the **one** embedding model |
| `DESCRIBE_DIAGRAMS` | `true` | vision diagram descriptions |
| `ALIGN_TOP_K` / `RETRIEVE_TOP_N` | `3` / `5` | alignment fan-out / search cap |
| `QDRANT_URL` · `DATABASE_URL` · `S3_BUCKET` | — | prod: vectors / registry / images |
| `CORS_ORIGINS` | localhost | SPA origin(s) in prod |

Frontend: `VITE_API_BASE` = backend origin (blank in dev → Vite proxy).

## Deploy

[`render.yaml`](render.yaml) deploys the backend to **Render** (Docker, context `backend/`, health
`/api/health`); the SPA goes to **Vercel** ([`vercel.json`](frontend/vercel.json)). Production state lives in
**Supabase** (Postgres registry), **Qdrant Cloud** (vectors), and **AWS S3** (diagram images), so the API
is stateless and scales. After first deploy with `DATABASE_URL`, run `python scripts/init_db.py` once.

## Non-negotiables

Core merge first · every block has a `reason` (honest, explainable AI) · source-label everything &
emphasize spoken-only · **raw audio never persisted** · per-course persistence · one embedding model ·
validate on the real demo lecture. (See `.specify/memory/constitution.md`.)

## License

<!-- TODO: confirm — no LICENSE file in repo. --> TBD.
