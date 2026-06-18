# EchoNotes — Project Context

> Context for OpenSpec. Describes the system as it is built today (stack, layout,
> conventions) so specs and changes reason against reality. Behavioral truth lives
> in the capability specs under `openspec/specs/`.

## What it is

EchoNotes merges a lecture's **audio** (what was said) with its **slides** (what was
written) into one **source-labeled, topic-organized** study document, and persists
notes **per course** so later lectures can build on earlier ones. Every output block
carries a source label (`slides` / `spoken` / `diagram`) and an explainable reason;
spoken-only content is emphasized. Raw audio is discarded after transcription.

## Tech stack

**Backend** (`backend/`, package `app.*`): Python + FastAPI.
- Transcription: Whisper / hosted STT.
- Slides: PyMuPDF (text + image extraction).
- One embedding model for both alignment and retrieval (never mix embedding spaces).
- Vector store: Chroma (local) / Qdrant (hosted) — pluggable.
- Object storage for preserved diagram images: local filesystem / S3-compatible (R2).
- Registry persistence: JSON file (local dev) / Postgres (prod) — pluggable.
- LLM for merge/refinement and a vision-capable LLM for diagram descriptions.
- Auth: bcrypt password hashing, PyJWT session tokens, Google id_token verification
  (PyJWKClient), email OTP / reset link via stdlib SMTP (console fallback in dev).

**Frontend** (`frontend/`): React + Vite + TypeScript, React Query, React Router,
Radix UI, Tailwind-style utility CSS. Talks to the backend over the JSON API only.

**Deploy**: Render (backend Docker, `render.yaml`), Vercel (frontend). CI in
`.github/workflows/ci.yml` runs hermetic backend (pytest) + frontend (vitest + tsc).

## Repository layout

- `backend/` — the FastAPI app. **Run all backend commands from `backend/`** (CWD-relative
  paths like `./data` / `./.chroma` and `from app...` imports assume it). Holds `app/`,
  `scripts/`, `samples/` (the demo lecture), `requirements*.txt`, `Dockerfile`, `.env*`.
- `frontend/` — the React SPA.
- Root — `render.yaml`, `openspec/` (specs + changes), `graphify-out/` (code-structure map),
  `README.md`, `CLAUDE.md`.

## Module map (backend `app/`)

`ingest · transcribe · slides · diagrams · embed · align · merge · refine · render ·
pipeline · retrieve · store (+ storage/ backends) · api (courses, lectures) · web ·
auth (security, service, google, deps, schemas, router) · email · config · main`.

## Conventions

- JSON API under `/api`; errors use the envelope `{"error": {"code", "message"}}`.
- All secrets come from environment only, with safe blank/dev defaults so local dev runs
  with zero external services (blank SMTP/OAuth/JWT → console email, dev JWT, hidden Google
  button). Never store or log plaintext passwords, OTPs, or tokens.
- Multi-tenant: every `Course` has an `owner_id`; data routes require a session (else 401)
  and are owner-scoped (non-owned → 404, never 403). The owner filter is enforced in the
  storage layer, not only in routes.
- Persistence is per-course; raw audio is never persisted.
- Tests are hermetic: they force local backends and mock all external I/O (no secrets,
  no network). First prod deploy with `DATABASE_URL` runs `scripts/init_db.py` once
  (and `scripts/migrate_add_owner.py` for pre-ownership data).

## Tooling

- **OpenSpec** — intent/spec memory. Baseline capability specs in `openspec/specs/`;
  proposed changes (proposal/design/tasks + spec deltas) in `openspec/changes/`.
  Workflow commands: `/opsx:explore`, `/opsx:propose`, `/opsx:apply`, `/opsx:archive`.
- **Graphify** — code-structure memory. Queryable graph at `graphify-out/graph.json`
  (+ `GRAPH_REPORT.md`); rebuilt after each commit by the installed post-commit hook.
