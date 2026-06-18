# CLAUDE.md — Agent Context for EchoNotes

## Project
EchoNotes — merges a lecture's audio (what was said) with its slides (what was written) into one source-labeled, topic-organized study document; persists notes per course so lectures build on each other.

## Spec & structure workflow
This project uses **OpenSpec** for intent and **Graphify** for code structure. Keep both fresh — a drifted spec or stale graph misleads.
- **Intent (OpenSpec):** baseline capability specs are the source of truth for what each part of the system SHALL do — `openspec/specs/<capability>/spec.md` (e.g. `note-merge`, `tenant-isolation`, `transcription`). Project context is in `openspec/project.md`. Proposed changes (proposal / design / tasks + spec deltas) live in `openspec/changes/`. Per-feature loop: `/opsx:explore` → `/opsx:propose` → `/opsx:apply` → `/opsx:archive`.
- **Before changing code:** read the relevant capability spec for intended behavior, then consult the graph for dependencies / blast radius (see `## graphify`). After a behavior change, update the spec by archiving a change so the baseline stays accurate.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).

## Active Technologies
- Python + FastAPI (backend)
- Whisper / hosted STT (transcription) — raw audio discarded after transcription
- PyMuPDF (PDF text + image extraction)
- One embedding model for both alignment and retrieval — keep constant
- Vector store: Chroma (local) / Qdrant (hosted) — pluggable
- Object storage for preserved diagram images: local / S3-compatible (R2)
- Registry persistence: JSON file (local) / Postgres (prod)
- Vision-capable LLM (diagram descriptions; Strong) · LLM (merge / refine)
- Auth + multi-tenancy: bcrypt password hashing, PyJWT (session JWT + Google id_token verification via PyJWKClient), email OTP / reset link (stdlib SMTP, console-log fallback in dev)
- Frontend: React + Vite + TypeScript, React Query, React Router, Radix UI
- Deploy: Render (backend Docker) + Vercel (frontend)

## Project layout
- `backend/` — the FastAPI app (`backend/app/`, package imported as `app.*`), `backend/scripts/`, `backend/samples/` (demo lecture), `backend/requirements*.txt`, `backend/Dockerfile`, `backend/.env*`, and local state `backend/data/` + `backend/.chroma/`. **Run all backend commands from `backend/`** (CWD-relative paths like `./data`/`./.chroma` and `from app...` imports assume it).
- `frontend/` — the React SPA; talks to the backend over the JSON API only.
- Root holds `render.yaml` (builds with `backend/` as Docker context), `openspec/` (specs + changes), `graphify-out/` (code-structure map), and docs.

## Module map
`ingest · transcribe · slides · diagrams · embed · align · merge · refine · render · pipeline · retrieve · store (+ storage/ backends) · api (courses, lectures) · web · auth (security, google, service, deps, schemas, router) · email · config · main` (under `backend/app/`). Behavioral detail for each area lives in `openspec/specs/<capability>/spec.md`; the storage facade `store.py` + `storage/` backends hold User + AuthToken and the per-Course `owner_id`.

## Working agreements
- Validate on the real demo lecture (`backend/samples/`) — a feature isn't done until shown on real data.
- Keep retrieved cross-lecture context to the top few chunks.
- Filter decorative images before describing or placing them.
- Confirm current library/API versions before coding (training knowledge may be stale).
- Tests are hermetic (force local backends, mock external I/O); secrets come from env only.
