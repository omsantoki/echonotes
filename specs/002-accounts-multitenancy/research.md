# Research & Decisions: Accounts & Multi-Tenancy

<!-- Spec Kit artifact: specs/002-accounts-multitenancy/research.md
Captures the spec §11 resolutions and the key auth decisions with rationale and
alternatives. Mirrors ../001-echonotes-core/research.md. -->

## Resolved clarifications (from spec §11)

| Question | Decision | Rationale |
|---|---|---|
| Password hasher | **bcrypt** (sha256 pre-hash) | Vetted + already installed (5.0.0); pre-hash removes the 72-byte truncation |
| Session mechanism | **Stateless JWT** (HS256, PyJWT) w/ expiry | No session table; simplest correct path; refresh = Stretch |
| Google id_token verify | **PyJWT `PyJWKClient`** vs Google JWKS | Server-side cert verification without the heavier `google-auth` dependency tree |
| Email transport | **stdlib `smtplib`**, console fallback | Gmail App Password works; blank SMTP = print to log (local-first, Art. IX) |
| Bootstrap owner for legacy courses | One admin user (`BOOTSTRAP_ADMIN_EMAIL`) via migration | Don't drop data; one documented mapping |

## Confirmed library versions (Day-of, 2026-06)

- **PyJWT 2.13.0** (`PyJWT[crypto]` pulls `cryptography` for RS256 — needed for Google verify).
- **bcrypt 5.0.0** (already in the venv).
- **smtplib** — stdlib, no version concern.
- **No `google-auth`** — `PyJWKClient` covers Google id_token verification.

## Decision log

### D-8 — 404, not 403, for resources the caller does not own
**Decision:** Reads/deletes/searches/uploads against a course or lecture the caller does not own return
the **same 404** a missing resource returns; only a missing session returns 401.
**Alternatives:** 403 Forbidden (leaks existence — a probe learns the id is real).
**Rationale:** Article X — existence is not leaked. Uniformity also simplifies the client.

### D-9 — Push the owner filter into the storage layer
**Decision:** `owner_id` is filtered in the registry (`WHERE owner_id = ?` / JSON predicate), not only in
the route. Routes call `store.*(..., owner_id=user.id)`.
**Alternatives:** filter only in routes (one forgotten check = a cross-tenant leak).
**Rationale:** Defense-in-depth; a single chokepoint enforces isolation for every backend and route.

### D-10 — Tokens (OTP / set-password / reset) hashed at rest, single-use, short-TTL
**Decision:** Store only `sha256(secret)`; the plaintext is emailed/returned once. Single active token per
(user, kind); consuming sets `used`; expired/used/over-attempt tokens are rejected.
**Alternatives:** store plaintext OTPs (rejected — Art. X); long-lived tokens (replay risk).
**Rationale:** Art. X secret hygiene; bounds brute-force and replay.

### D-11 — No email enumeration
**Decision:** signup and forgot-password always return the same neutral 200 regardless of whether the email
exists; login returns one generic `invalid_credentials` for unknown-email and wrong-password alike.
**Rationale:** Don't turn the auth surface into an account-existence oracle.

### D-12 — Reuse the 001 storage facade; no new persistence subsystem
**Decision:** Users + auth tokens live in the existing registry backend (JSON / Postgres) behind
`app/store.py`; the vector and object backends are untouched.
**Rationale:** One persistence story (D-2 of 001); the owner gate at the Course boundary makes the
course-scoped vector store automatically tenant-safe (FR-24).

### D-13 — `web.py` (server-rendered console) binds to the bootstrap owner
**Decision:** The multi-tenant product surface is the React SPA + JSON API. The built-in server-rendered
UI (`web.py`) is a single-tenant local/admin console bound to the bootstrap admin owner.
**Alternatives:** full cookie-session auth in `web.py` (scope creep); leave it listing all courses
(cross-tenant leak — rejected).
**Rationale:** Keeps 001's T019/T021 console working locally without leaking across tenants or duplicating
the auth UI.

## Open research tasks (confirm before deploy)

- Confirm the deploy platform allows outbound SMTP (some PaaS block port 25/587) — else use a transactional
  email API or accept console email for the demo.
- Confirm the Google OAuth client id is a **Web** client and the SPA origin is in its authorized origins.
- Re-confirm PyJWT / bcrypt versions at deploy time (pin in requirements.txt).
