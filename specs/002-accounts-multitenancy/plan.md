# Implementation Plan: Accounts & Multi-Tenancy

<!--
Spec Kit artifact: specs/002-accounts-multitenancy/plan.md
Output of the /speckit.plan step. The technical "HOW". Must pass the
Constitution Check before tasks are generated. Reuses the 001 storage facade
pattern (app/store.py + storage/ backends) — no shortcuts around it.
-->

**Feature branch:** `002-accounts-multitenancy`
**Input:** spec.md · **Governs:** constitution.md (esp. Article X) · **Builds on:** 001-echonotes-core/plan.md

---

## Technical Context

001 is a pipeline app whose persistence is a storage facade (`app/store.py`) over three
pluggable backends (vectors / registry / objects), each chosen by env. This feature adds:

1. a **User** entity + **auth tokens** (OTP / set-password / reset) to the *registry* backend,
2. an **owner** on every Course, with the owner filter pushed **down into the registry**,
3. an **`app/auth/`** module (an `APIRouter` mounted at `/api/auth`) and an **`app/email.py`** sender.

No new persistence subsystem is introduced — users and tokens live in the same registry as
courses/lectures (registry.json locally, Postgres in prod). With JWT/SMTP/OAuth env all blank,
local dev still runs end-to-end (dev JWT secret, console email, Google button hidden) — the same
"blank env = local dev" guarantee 001 established.

**Note on stack:** versions change — confirm before coding (research.md). Confirmed for this build:
PyJWT 2.13.0 (sessions + Google id_token via `PyJWKClient`), bcrypt 5.0.0 (password hashing),
stdlib `smtplib` (email). No google-auth dependency.

| Concern | Choice | Rationale |
|---|---|---|
| Password hashing | bcrypt (sha256 pre-hash) | Vetted, already installed; pre-hash sidesteps the 72-byte limit |
| Session | JWT HS256 w/ expiry (PyJWT) | Stateless, no session table; secret from env |
| OTP / reset / set-password tokens | random secret, **sha256-hashed at rest**, short TTL, single-use | FR-15/16/17/27/28; never plaintext |
| Email | stdlib `smtplib` (SMTP); console fallback | Gmail App Password works; blank SMTP = print to log |
| Google verify | PyJWT `PyJWKClient` vs Google JWKS | Server-side cert verification, no extra heavyweight dep |
| Users/tokens storage | existing registry backend (JSON / Postgres) | Reuse the 001 facade; no new subsystem |
| Frontend auth | React Context + React Query + Google Identity Services (script) | Matches 001 frontend patterns; no new npm dep |

## Constitution Check

| Article | Compliance |
|---|---|
| I — Problem fidelity | Core merge (001) untouched; accounts wrap it, never replace it |
| II — Honest AI / no theater | Auth does real work: verified email, hashed secrets, server-side Google verify |
| III — Source labeling | Unchanged — labels still on every block |
| IV — Store notes not audio | Unchanged — audio still discarded after transcription |
| V — Continuity by design | Per-course persistence preserved; now per-user-per-course |
| VI — One embedding model | Unchanged |
| VII — Tiered scope | Core = signup/OTP/login + isolation; Strong = forgot/reset + Google; Stretch = polish |
| VIII — Demoable on real data | New user signs up → processes the real demo lecture (backend/samples/) |
| IX — Ship public & simple | Reuses one storage facade; landing stays public; minimal auth UI |
| **X — Tenant isolation & secret hygiene** | This feature *is* Article X: per-user isolation (404 not 403); no plaintext secrets; env-only secrets; blank-env dev |

✅ No violations. Proceed to `/speckit.tasks`.

## Architecture Overview

```
                       ┌──────────────── /api/auth (app/auth/router.py) ───────────────┐
 Browser (React SPA)   │ signup → verify-otp → set-password → login → me               │
   AuthContext ───────▶│ google · forgot-password · reset-password                     │
   Bearer <JWT>        └──┬───────────────┬──────────────────┬───────────────────┬─────┘
                          │               │                  │                   │
                   auth/service.py   auth/security.py   auth/google.py        email.py
                   (find/create,     (bcrypt hash,      (PyJWKClient vs       (SMTP or
                    issue tokens)     JWT, OTP, hashes)   Google JWKS)         console)
                          │
                          ▼
        store.py facade ──▶ registry backend (JSON | Postgres)
          users · auth_tokens · courses(owner_id) · lectures · diagrams

 Data routes (courses/lectures/search/upload/delete)
   └─ Depends(get_current_user) ─▶ store.*(..., owner_id=user.id)  ─▶ owner filter pushed into registry
        no session → 401 · not-owned → 404
```

## Module Breakdown

New / changed modules (under `backend/app/`):

1. **auth/** *(new package)* — the auth surface.
   - `security.py` — password hash/verify (bcrypt + sha256 pre-hash), JWT encode/decode, OTP
     generation, token mint + sha256 hashing, TTL helpers.
   - `google.py` — `verify_google_id_token(id_token)` via `PyJWKClient` against Google's JWKS
     (audience + issuer checked). Easily monkeypatched in tests.
   - `service.py` — business logic for signup / verify-otp / set-password / login / google /
     forgot / reset; talks to `store` + `email`.
   - `deps.py` — `get_current_user` FastAPI dependency (decodes the Bearer JWT → User; 401 otherwise).
   - `schemas.py` — request/response Pydantic models.
   - `router.py` — the `APIRouter(prefix="/api/auth")`, mounted in `main.py`.
2. **email.py** *(new)* — `send_email(...)` over SMTP with a console-log fallback; `send_otp_email`,
   `send_reset_email` helpers. Never logs secrets except the dev OTP/link fallback (by design).
3. **models.py** *(changed)* — add `User`, `AuthToken`, `AuthProvider`/`TokenKind` enums; add
   `owner_id` to `Course`.
4. **config.py** / `.env.example` *(changed)* — add `jwt_secret`, `jwt_expiry`, SMTP settings,
   `google_oauth_client_id`, `frontend_url`, `otp_ttl`, `reset_token_ttl`, `bootstrap_admin_email`.
5. **storage/base.py, registry_json.py, registry_pg.py** *(changed)* — add User + AuthToken methods
   to the `RegistryBackend` Protocol and both backends; push the `owner_id` filter into course/lecture
   reads/lists/deletes. `scripts/init_db.py` gains `users` + `auth_tokens` tables and `courses.owner_id`.
6. **store.py** *(changed)* — facade methods for users/tokens; owner-scoped course/lecture functions.
7. **api/courses.py, api/lectures.py, ingest.py** *(changed)* — `Depends(get_current_user)`; pass
   `owner_id`; 404 for non-owned. **main.py** mounts the auth router; **web.py** binds to the bootstrap
   owner (single-tenant server console; the multi-tenant surface is the SPA + JSON API).
8. **scripts/migrate_add_owner.py** *(new)* — create the bootstrap admin user and assign all ownerless
   courses to it (FR-25).

## Data Model (summary; full detail in data-model.md)

- **User** (id, email[unique, lowercase], password_hash?, email_verified, auth_provider[local|google],
  google_sub?, created_at)
- **AuthToken** (id, user_id, kind[otp|set_password|reset], token_hash, expires_at, attempts, used, created_at)
- **Course** *(changed)* gains **owner_id** (FK → User). Legacy ownerless courses → bootstrap admin.
- No new vector/object entities. Audio still never persisted (Art. IV).

## API Contracts (summary; full detail in contracts/)

- `POST /api/auth/signup` · `POST /api/auth/verify-otp` · `POST /api/auth/set-password`
- `POST /api/auth/login` · `POST /api/auth/google` · `GET /api/auth/me`
- `POST /api/auth/forgot-password` · `POST /api/auth/reset-password`
- **Ownership changes to 001 routes** (see ../001-echonotes-core/contracts/api.md + contracts/api.md here):
  every `/api/courses*` and `/api/lectures*` route now requires a session (401) and is owner-scoped
  (404 for non-owned).

## Phasing (tier split — Constitution Art. VII)

- **Core:** email+password signup → OTP verify → set password → login (session token); `GET /me`;
  per-user isolation of courses/lectures/notes/search (owner filter in storage); landing-page corner
  CTA + route guards. Email via console fallback.
- **Strong:** forgot-password → emailed reset link → reset; "Continue with Google".
- **Stretch:** refresh-token rotation; rate-limit/lockout polish; account-settings page.

## Risks & Mitigations (from spec §9)

- Existence leakage → uniform responses + 404-not-403 (enforced in storage).
- Token abuse → hashed, single-use, short-TTL, attempt-limited tokens.
- Local dev friction → console email, dev JWT secret, hidden Google button when unconfigured.
- Legacy data loss → documented bootstrap-owner migration (idempotent script).

## Quickstart

See `quickstart.md` for env setup (JWT/SMTP/Google), running the full signup→login flow locally
with console email, the legacy-course migration, and the two-user isolation check.
