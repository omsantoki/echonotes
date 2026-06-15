# CLAUDE.md — Agent Context for EchoNotes

<!--
Spec Kit maintains an agent context file (CLAUDE.md / GEMINI.md / .cursor/rules,
depending on your agent) so the coding assistant stays aware of the active stack
and rules. Normally updated by the /speckit.plan step. This is the EchoNotes version.
-->

## Project
EchoNotes — merges a lecture's audio (what was said) with its slides (what was written) into one source-labeled, topic-organized study document; persists notes per course so lectures build on each other.

## Non-negotiables (see .specify/memory/constitution.md)
1. Core merge first; nothing else until it works on the demo lecture.
2. Honest, explainable AI — every block carries a `reason`. No chatbot-wrapper framing.
3. Source-label every block: `slides` / `spoken` / `diagram`. Emphasize spoken-only content.
4. Never persist raw audio — discard after transcription.
5. Persistence is per-course from day one.
6. One embedding model for both alignment and retrieval.
7. Respect the tiers: Core → Strong → Stretch. Cut from the edges, never the core.

## Active Technologies
- Python + FastAPI (backend)
- Whisper / hosted STT (transcription)
- PyMuPDF (PDF text + image extraction)
- One embedding model (alignment + retrieval) — keep constant
- Chroma (vector store; primary persistence) — hosted option for deploy
- Vision-capable LLM (diagram descriptions; Strong)
- LLM API (merge/composition)
- Minimal React or server-rendered UI; Markdown/HTML output
- Render/Railway (+ Vercel if split) for public deploy

## Project layout
- `backend/` — the FastAPI app (`backend/app/`, package imported as `app.*`), `backend/scripts/`,
  `backend/samples/` (demo lecture), `backend/requirements*.txt`, `backend/Dockerfile`, `backend/.env*`,
  and local state `backend/data/` + `backend/.chroma/`. **Run all backend commands from `backend/`**
  (CWD-relative paths like `./data`/`./.chroma` and `from app...` imports assume it).
- `frontend/` — the React SPA; talks to the backend over the JSON API only.
- Root holds `render.yaml` (builds with `backend/` as Docker context), `specs/`, `.specify/`, and docs.

## Module map
ingest · transcribe · slides · diagrams · embed · align · merge · store · retrieve · api · web
(under `backend/app/`; see specs/001-echonotes-core/plan.md)

## Working agreements
- Validate on the real demo lecture (backend/samples/) — a feature isn't done until shown on real data.
- Keep retrieved cross-lecture context to the top few chunks.
- Filter decorative images before describing or placing them.
- Confirm current library/API versions before coding (training knowledge may be stale).

## Recent changes
- Reorganized the repo into top-level `backend/` (Python API) + `frontend/` (React SPA); run backend commands from `backend/`.
- Initialized spec, plan, data-model, contracts, tasks for `001-echonotes-core`.
