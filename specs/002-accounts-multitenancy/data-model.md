# Data Model: Accounts & Multi-Tenancy

<!-- Spec Kit artifact: specs/002-accounts-multitenancy/data-model.md
Extends specs/001-echonotes-core/data-model.md. New entities (User, AuthToken)
live in the structural **registry** backend (registry.json locally, Postgres in
prod) — NOT the vector store. The Course entity gains an owner. Raw audio is
still never an entity (Constitution Art. IV); secrets are never stored in
plaintext (Article X). -->

The 001 model is embeddings-first for *notes*; identity is structural and lives in the
registry alongside Course/Lecture/DiagramAsset. This feature adds **User** and **AuthToken**
there, and adds **owner_id** to **Course**.

## New entities

### User
| Field | Type | Notes |
|---|---|---|
| id | string (uuid) | PK |
| email | string | **unique**, normalized to **lowercase** before store/compare |
| password_hash | string? | bcrypt hash (with sha256 pre-hash); **null** for Google-only accounts until they set one |
| email_verified | bool | false until OTP (local) or Google verifies it |
| auth_provider | enum | `local` \| `google` (how the account was created/links) |
| google_sub | string? | Google subject id; set for `google` accounts; unique when present |
| created_at | datetime | |

**Constraints / rules**
- `email` is unique and lowercased; lookups normalize first (so `A@x.com` == `a@x.com`).
- A `local` account is unusable until `email_verified = true` AND `password_hash` is set.
- A `google` account is created with `email_verified = true` and `password_hash = null`;
  it may later set a password via forgot-password (then it can also log in with a password).
- **Passwords are never stored or logged in plaintext.** Hashing: `bcrypt(base64(sha256(password)))`
  — the sha256 pre-hash removes bcrypt's 72-byte input truncation while keeping a vetted hasher (Art. X).

### AuthToken  *(short-lived, hashed, single-use credentials — never plaintext)*
| Field | Type | Notes |
|---|---|---|
| id | string (uuid) | PK |
| user_id | string | FK → User |
| kind | enum | `otp` \| `set_password` \| `reset` |
| token_hash | string | **sha256 of the secret** (the 6-digit OTP, or the random URL token). The plaintext is emailed/returned **once** and never stored. |
| expires_at | datetime | TTL: OTP ≈ `otp_ttl` (~10 min); set-password ≈ `reset_token_ttl`; reset ≈ `reset_token_ttl` |
| attempts | int | incremented on each failed check; rejected once over the limit (OTP brute-force guard) |
| used | bool | set true when consumed; a used token is rejected (single-use) |
| created_at | datetime | |

**Constraints / rules**
- Tokens store only the **sha256 hash**; verification re-hashes the presented secret and compares.
- **Single-use:** consuming a token sets `used = true`; used/expired tokens are rejected.
- **No reuse / one active at a time:** issuing a new token of a kind for a user **invalidates** any
  prior unused tokens of that kind (so an old OTP/reset link can't be replayed).
- **OTP:** 6 digits, `otp_ttl` TTL, attempt-limited (`otp_max_attempts`). Looked up by `(user_id, kind=otp)`.
- **set_password / reset:** high-entropy random URL-safe token. Looked up by `(token_hash, kind)` so the
  raw value never needs to be stored.
- Expired tokens may be cleaned up lazily; correctness does not depend on a sweeper.

### Course *(changed — see ../001-echonotes-core/data-model.md)*
| Field | Type | Notes |
|---|---|---|
| id | string (uuid) | PK |
| name | string | |
| **owner_id** | **string** | **FK → User** — the sole owner; set to the creator. **Nullable only transiently** for pre-migration legacy rows (see Migration). |
| created_at | datetime | |

All other 001 entities (Lecture, NoteChunk, DiagramAsset) are unchanged in shape; their ownership
is **derived** through `Course.owner_id` (a lecture/diagram/chunk belongs to whoever owns its course).

## Relationships

```
User 1───* Course 1───* Lecture 1───* NoteChunk
                   │                        (course_id denormalized on chunk, as in 001)
                   └───* DiagramAsset
User 1───* AuthToken
```

Ownership is enforced at the **Course** boundary: a Lecture/NoteChunk/DiagramAsset is accessible iff
the caller owns the Course it belongs to. The owner filter is pushed **into the registry** (SQL `WHERE
owner_id = ?` / JSON predicate), not applied only in the route (FR-23, Art. X).

## Migration of existing "common" courses (FR-25)

Pre-feature, all courses are global with no `owner_id`. We must not drop them.

1. A one-shot, idempotent script (`backend/scripts/migrate_add_owner.py`) ensures a **bootstrap admin
   user** exists (email from `BOOTSTRAP_ADMIN_EMAIL`, default `admin@echonotes.local`,
   `auth_provider=local`, `email_verified=true`, no usable password unless one is set via reset).
2. Every course with a missing/null `owner_id` is assigned to that bootstrap admin.
3. Postgres: `scripts/init_db.py` adds `courses.owner_id TEXT` (idempotent `ADD COLUMN IF NOT EXISTS`)
   and the `users` / `auth_tokens` tables; the migration then backfills `owner_id`.
4. Read-time safety net: the owner filter is strict equality, so a course whose `owner_id` is still
   null matches **no** user and is never returned to anyone until the migration backfills it — an
   un-migrated DB therefore cannot leak legacy courses to an arbitrary user (it just hides them until
   the migration assigns them to the bootstrap admin).

The bootstrap admin can log in by running forgot-password against `BOOTSTRAP_ADMIN_EMAIL` (reset link in
the log) to claim a password — the legacy library is then a normal owned library.

## Validation rules

- Every Course MUST resolve to an `owner_id` (creator, or bootstrap admin for legacy rows).
- Every User `email` is unique + lowercase; `auth_provider` ∈ {local, google}.
- A `set_password`/`reset` token is valid only if not `used`, not expired, and matches by hash.
- An `otp` token is valid only if not `used`, not expired, under the attempt limit, and matches by hash.
- No NoteChunk/Lecture/Diagram is ever returned for a course the caller does not own (404, not 403).

## Lifecycle of secrets (explicit — Art. X)

`password → sha256 pre-hash → bcrypt → stored hash` (plaintext discarded).
`OTP/reset secret → emailed once (or logged in dev) → sha256 → stored hash` (plaintext never stored).
`session → signed JWT (HS256) with expiry → held client-side` (no server session row).
Secrets (JWT secret, SMTP creds, Google client id) come from **env only**; none are persisted to the
registry or written to logs (the dev OTP/link console fallback is the sole, deliberate exception).
