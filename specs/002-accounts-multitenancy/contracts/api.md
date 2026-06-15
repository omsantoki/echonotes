# API Contracts: Accounts & Multi-Tenancy

<!-- Spec Kit artifact: specs/002-accounts-multitenancy/contracts/api.md
The /api/auth/* surface, plus the ownership-scoped changes to the 001 routes.
Same error envelope as 001: { "error": { "code": string, "message": string } }.
Cross-ref: ../001-echonotes-core/contracts/api.md (updated for auth/ownership). -->

## Conventions
- Base path: `/api`. JSON unless noted.
- Errors: `{ "error": { "code": string, "message": string } }`.
- **Session:** authenticated requests send `Authorization: Bearer <jwt>`. A `session_token` is a
  signed JWT (HS256) with an expiry; clients store it and attach it to every data request.
- **Auth status codes:** missing/invalid/expired session on a gated route → **401** `unauthorized`.
  A resource the caller does not own → **404** `*_not_found` (existence is never leaked; not 403).
- Email enumeration is avoided: signup and forgot-password never reveal whether an email exists.

---

## Auth endpoints (`/api/auth/*`)

### POST /api/auth/signup   *(Core, FR-14/15)*
Begin signup. Creates an unverified user (if new) and emails a 6-digit OTP (console in dev).
**Body:** `{ "email": string }`
**200:** `{ "ok": true, "message": "If that email can sign up, a verification code is on its way." }`
*(Always 200 with the same message whether or not the email already existed — no enumeration.)*

### POST /api/auth/verify-otp   *(Core, FR-16)*
Verify the emailed code.
**Body:** `{ "email": string, "otp": string }`
**200:** `{ "set_password_token": string }`  — short-lived, single-use; used by set-password.
**400:** `{ "error": { "code": "invalid_otp", "message": string } }` — wrong/expired/too-many-attempts.

### POST /api/auth/set-password   *(Core, FR-17)*
Set the initial password using the token from verify-otp; logs the user in.
**Body:** `{ "token": string, "password": string }`
**200:** `{ "session_token": string, "user": { "id", "email", "auth_provider", "email_verified" } }`
**400:** `{ "error": { "code": "invalid_token" | "weak_password", "message": string } }`

### POST /api/auth/login   *(Core, FR-18)*
**Body:** `{ "email": string, "password": string }`
**200:** `{ "session_token": string, "user": { "id", "email", "auth_provider", "email_verified" } }`
**401:** `{ "error": { "code": "invalid_credentials", "message": "Invalid email or password." } }`
   — same response for unknown email, wrong password (no which-field/existence leak).
**403:** `{ "error": { "code": "email_not_verified", "message": "Verify your email first." } }`
   — account exists and password matches but email is unverified.

### POST /api/auth/google   *(Strong, FR-26)*
Verify a Google ID token server-side (against Google's certs; audience = configured client id),
then find-or-create a verified user linked by `google_sub`.
**Body:** `{ "id_token": string }`
**200:** `{ "session_token": string, "user": { ... } }`
**400:** `{ "error": { "code": "invalid_google_token", "message": string } }`
**503:** `{ "error": { "code": "google_not_configured", "message": string } }` — server has no client id.

### POST /api/auth/forgot-password   *(Strong, FR-27)*
**Body:** `{ "email": string }`
**200:** `{ "ok": true, "message": "If that account exists, a password reset link is on its way." }`
*(Always 200, neutral message — no enumeration. If the account exists, a reset link is emailed /
logged; the link points at `${FRONTEND_URL}/reset-password?token=…`.)*

### POST /api/auth/reset-password   *(Strong, FR-28)*
**Body:** `{ "token": string, "password": string }`
**200:** `{ "ok": true }` — password updated, token consumed (single-use).
**400:** `{ "error": { "code": "invalid_token" | "weak_password", "message": string } }`

### GET /api/auth/me   *(Core, FR-19)*
**Headers:** `Authorization: Bearer <session_token>`
**200:** `{ "id", "email", "auth_provider", "email_verified", "created_at" }`
**401:** `{ "error": { "code": "unauthorized", "message": string } }`

### User object (shared shape)
```json
{ "id": "string", "email": "string", "auth_provider": "local|google",
  "email_verified": true, "created_at": "string" }
```

---

## Ownership-scoped changes to the 001 routes

Every route below now **requires** `Authorization: Bearer <session_token>` and is **scoped to the
owner**. The request/response bodies are otherwise as in ../001-echonotes-core/contracts/api.md.

| Route | No session | Not owner | Owner |
|---|---|---|---|
| `POST /api/courses` | 401 | — | 201, course owned by caller |
| `GET /api/courses` | 401 | — | 200, **only the caller's** courses |
| `GET /api/courses/{id}` | 401 | **404** | 200 |
| `DELETE /api/courses/{id}` | 401 | **404** | 204 |
| `GET /api/courses/{id}/search?q=` | 401 | **404** | 200 (spans only this owner's lectures) |
| `POST /api/lectures` (multipart, has `course_id`) | 401 | **404** (course not owned) | 202 |
| `GET /api/lectures/{id}` | 401 | **404** | 200 |
| `GET /api/lectures/{id}/export` | 401 | **404** | 200 (file) |
| `DELETE /api/lectures/{id}` | 401 | **404** | 204 |

**Rules**
- `401 unauthorized` is returned **before** any ownership check when the session is missing/invalid.
- Non-owned course/lecture access returns the **same 404** (`course_not_found` / `lecture_not_found`)
  a truly-missing resource returns — existence is not leaked (FR-23, Art. X).
- The owner filter is applied in the **storage layer** (registry `WHERE owner_id = ?` / JSON predicate),
  so it holds regardless of which route or backend is in play; routes do not filter on their own.
- `GET /api/courses/{id}/search` and the merge-time "builds-on" retrieval only ever query within a course
  the caller owns; they never cross tenants (FR-24).
- `/api/health` stays **public** (liveness only; it already reveals no secrets and no per-user data).
- The `/assets/{lecture_id}/{asset_id}.{ext}` image mount stays as in 001 (opaque uuids; not directory-listable).

## Contract notes
- The auth endpoints are unauthenticated **except** `GET /api/auth/me`.
- All error bodies use the 001 envelope; new codes: `invalid_otp`, `invalid_token`, `weak_password`,
  `invalid_credentials`, `email_not_verified`, `invalid_google_token`, `google_not_configured`,
  `unauthorized`.
- No endpoint ever returns a password hash, an OTP, a raw token, or a `token_hash` (Art. X).
