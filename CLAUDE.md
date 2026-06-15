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
8. Tenant isolation (Art. X): a user only ever sees their own data. Every Course has an `owner_id`;
   data routes require a session (401) and are owner-scoped (404 for non-owned — never 403). No plaintext
   passwords/OTPs/tokens; secrets via env only; local dev runs with blank SMTP/OAuth/JWT.

## Active Technologies
- Python + FastAPI (backend)
- Whisper / hosted STT (transcription)
- PyMuPDF (PDF text + image extraction)
- One embedding model (alignment + retrieval) — keep constant
- Chroma (vector store; primary persistence) — hosted option for deploy
- Vision-capable LLM (diagram descriptions; Strong)
- LLM API (merge/composition)
- Auth + multi-tenancy (feature 002): bcrypt password hashing, PyJWT (session JWT + Google id_token
  verification via PyJWKClient), email OTP / reset link (stdlib SMTP, console-log fallback in dev).
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
· auth (auth/{security,google,service,deps,schemas,router}) · email
(under `backend/app/`; see specs/001-echonotes-core/plan.md and specs/002-accounts-multitenancy/plan.md).
Storage facade `store.py` + `storage/` backends now also hold User + AuthToken and the per-Course `owner_id`.

## Working agreements
- Validate on the real demo lecture (backend/samples/) — a feature isn't done until shown on real data.
- Keep retrieved cross-lecture context to the top few chunks.
- Filter decorative images before describing or placing them.
- Confirm current library/API versions before coding (training knowledge may be stale).

## Recent changes
- Added feature `002-accounts-multitenancy`: user accounts (email+OTP signup → password, login,
  Google sign-in, forgot/reset) and per-user data isolation. New `app/auth/` + `app/email.py`; `User`
  + `AuthToken` models; `owner_id` on Course; all data routes gated by `get_current_user` and owner-scoped.
  Constitution amended (Article X). Spec: `specs/002-accounts-multitenancy/`. Local dev unchanged with
  blank SMTP/OAuth/JWT (console email, dev JWT secret, hidden Google button).
- Reorganized the repo into top-level `backend/` (Python API) + `frontend/` (React SPA); run backend commands from `backend/`.
- Initialized spec, plan, data-model, contracts, tasks for `001-echonotes-core`.
