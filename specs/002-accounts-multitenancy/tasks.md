# Tasks: Accounts & Multi-Tenancy

<!--
Spec Kit artifact: specs/002-accounts-multitenancy/tasks.md
Output of the /speckit.tasks step. Grouped by tier/phase (Constitution Art. VII),
ordered by dependency. [P] = parallelizable. IDs (T1xx) continue the project's
stable-reference scheme (001 used T001–T053) and trace back to spec.md FR-xx.
-->

**Feature:** `002-accounts-multitenancy` · **Governs:** constitution.md (Art. X), plan.md, spec.md
**Builds on:** `001-echonotes-core` tasks (T001–T053)

Legend: `[P]` = parallelizable · `[Core]/[Strong]/[Stretch]` = tier · `→ FR-xx` = requirement traced.

---

## Phase 0 — Setup & Foundations

- **T100** Add auth deps + config: `PyJWT[crypto]`, confirm `bcrypt`; add `jwt_secret`, `jwt_expiry`,
  SMTP (`smtp_host/port/user/password/from`), `google_oauth_client_id`, `frontend_url`, `otp_ttl`,
  `otp_max_attempts`, `reset_token_ttl`, `bootstrap_admin_email` to `Settings` with **safe blank/dev
  defaults**; update `.env.example`. (`config`, `requirements`) → FR-20, FR-29, FR-30
- **T101** [P] Define new models: `User`, `AuthToken`, `AuthProvider`/`TokenKind` enums; add `owner_id`
  to `Course` per data-model.md. (`models`) → FR-14, FR-21
- **T102** [P] `app/email.py`: `send_email` over SMTP with a **console-log fallback** when SMTP is
  blank; `send_otp_email`, `send_reset_email`. (`email`) → FR-29, FR-30
- **T103** `app/auth/security.py`: bcrypt hash/verify (sha256 pre-hash), JWT encode/decode w/ expiry,
  6-digit OTP gen, random token mint + sha256 hashing, TTL helpers. (`auth`) → FR-15, FR-17, FR-20, FR-30

## Phase 1 — [Core] Accounts + per-user isolation

> Goal: signup → OTP → set-password → login (session), and a user only ever sees their own data.
> Do not start Strong/Stretch until this works on the real demo lecture (Art. I/VII).

- **T110** [Core] Storage — users + tokens: add `create_user/get_user/get_user_by_email/
  get_user_by_google_sub/update_user` and `create_auth_token/find_auth_token/bump_auth_token/
  invalidate_auth_tokens` to the `RegistryBackend` Protocol and **both** `registry_json.py` and
  `registry_pg.py`; expose via `store.py`. (`storage/base`, `registry_json`, `registry_pg`, `store`)
  → FR-14–FR-17, FR-27, FR-28, FR-30
- **T111** [Core] Storage — owner scoping: thread `owner_id` into `list_courses(owner_id)`,
  `get_course(course_id, owner_id)`, `delete_course(course_id, owner_id)`, `get_lecture(lecture_id,
  owner_id)`, `delete_lecture(lecture_id, owner_id)` — filter **in the registry** (SQL `WHERE owner_id`
  / JSON predicate), not the route. Add an internal unscoped path for system tasks (lifespan recovery).
  (`storage/*`, `store`) → FR-21, FR-23, FR-24
- **T112** [Core] `scripts/init_db.py`: add `users` + `auth_tokens` tables and `courses.owner_id`
  (idempotent `ADD COLUMN IF NOT EXISTS`). (`scripts`) → FR-21, FR-25
- **T113** [Core] `app/auth/service.py` + `schemas.py`: signup, verify-otp, set-password, login,
  `me`; uniform no-enumeration responses; reject unverified login. (`auth`) → FR-14–FR-19
- **T114** [Core] `app/auth/deps.py`: `get_current_user` dependency (decode Bearer JWT → User; 401 on
  missing/invalid/expired). (`auth`) → FR-19, FR-22
- **T115** [Core] `app/auth/router.py` mounted at `/api/auth` in `main.py`: signup, verify-otp,
  set-password, login, me. (`auth`, `api`) → FR-14–FR-19
- **T116** [Core] Gate + scope the 001 routes: add `Depends(get_current_user)` and pass `owner_id` to
  `courses.py`, `lectures.py`, `ingest.py`; **404 (not 403)** for non-owned course/lecture; new courses
  owned by the creator. (`api/courses`, `api/lectures`, `ingest`) → FR-21–FR-24
- **T117** [Core] `web.py` + `main.py` lifespan: bind the server-rendered console to the bootstrap owner
  (single-tenant surface) and make the interrupted-lecture recovery scan use the unscoped system path so
  it doesn't depend on a user. (`web`, `main`) → FR-23, FR-25
- **T118** [Core] `scripts/migrate_add_owner.py`: ensure the bootstrap admin user exists and assign all
  ownerless courses to it (idempotent). (`scripts`) → FR-25
- **T119** [Core] Frontend auth core: `AuthContext` + `useAuth`; store the session token; extend
  `lib/http.ts` to attach `Authorization: Bearer` and, on 401, clear the session and redirect to
  `/login`; auth API methods in `lib/api.ts`; `types/api.ts` auth types. (`frontend`) → FR-19, FR-22
- **T120** [Core] Frontend pages: `LoginPage`, 3-step `SignUpPage` (email → OTP → password). (`frontend`)
  → FR-14–FR-18
- **T121** [Core] Frontend routing/guards (`routes.tsx`): keep `/` public; add public `/login`,
  `/signup`; wrap `/app`, `/courses/:id`, `/courses/:id/upload`, `/lectures/:id` in `RequireAuth`
  (redirect to `/login`, preserve intended destination). (`frontend`) → FR-22, US-11
- **T122** [Core] Header CTA in `AppShell`/`TopNav`: logged-out → small **Log in / Sign up**; logged-in →
  email + **Log out**; landing must NOT pop a login wall. (`frontend`) → US-11
- **T123** [Core] Per-user UI sanity: confirm course list/home/hooks have no leftover global-course
  assumption — they reflect only the signed-in user once the API is scoped. (`frontend`) → FR-23
- **T124** [Core] Tests — auth flows: signup happy path, wrong OTP, expired/used token, unverified login,
  duplicate email; `me` with/without token. (`tests`) → FR-14–FR-19
- **T125** [Core] Tests — isolation: user A cannot read/list/delete/search/upload-to user B's course →
  404; unauthenticated → 401; new course owned by creator. (`tests`) → FR-21–FR-24
- **T126** [Core] **Validation gate:** new user signs up (OTP from the log) → set password → log in →
  create a course → process the real demo lecture (backend/samples/) end-to-end, owned by them; a second
  user sees none of it (direct URL → 404). (`samples`) → US-8/9/10, FR-21–FR-25 — *MUST pass before Strong*

## Phase 2 — [Strong]

- **T130** [Strong] `app/auth/google.py`: `verify_google_id_token` via PyJWT `PyJWKClient` vs Google's
  JWKS (audience + issuer checked); `service.google_auth` find-or-creates a verified user by `google_sub`;
  `POST /api/auth/google`. (`auth`) → FR-26
- **T131** [Strong] [P] Forgot/reset: `service.forgot_password` (always 200, no enumeration; email a
  reset link to `${FRONTEND_URL}/reset-password?token=…`) + `service.reset_password` (single-use token);
  `POST /api/auth/forgot-password`, `POST /api/auth/reset-password`. (`auth`, `email`) → FR-27, FR-28
- **T132** [Strong] Frontend `ForgotPasswordPage` + `ResetPasswordPage` (reads token from URL); add
  public routes. (`frontend`) → FR-27, FR-28
- **T133** [Strong] Frontend "Continue with Google" via Google Identity Services (script); button hidden
  when no client id configured. (`frontend`) → FR-26
- **T134** [Strong] Tests — Google new-vs-existing user (mock the verifier); forgot→reset happy path +
  expired/used reset token. (`tests`) → FR-26, FR-27, FR-28

## Phase 3 — [Stretch]

- **T140** [Stretch] Refresh-token rotation (issue + rotate; revoke on logout). (`auth`, `frontend`) → FR-31
- **T141** [Stretch] [P] Rate-limit / lockout polish for login + OTP beyond the basic attempt cap. (`auth`) → FR-31
- **T142** [Stretch] [P] Account-settings page: change password; show email/provider. (`frontend`, `auth`) → FR-31

## Phase 4 — Ship & Demo

- **T150** Update docs: `quickstart.md` (this folder), `../001-echonotes-core` (data-model + contracts),
  `constitution.md` (Art. X), top-level `CLAUDE.md`. Reconcile specs ↔ shipped code. (`docs`)
- **T151** [P] Verify deploy env: set `JWT_SECRET`, SMTP (or accept console), `GOOGLE_OAUTH_CLIENT_ID`,
  `FRONTEND_URL`, `BOOTSTRAP_ADMIN_EMAIL`; run `init_db.py` + `migrate_add_owner.py` on the managed DB. (`/`)
- **T152** [P] Demo script: public landing → sign up → OTP in log → set password → process demo lecture →
  second user sees nothing → forgot/reset → Google. (`docs`)

---

## Dependency Summary

```
Setup (T100–T103)
  └─▶ Core (T110/T111 → T112 → T113/T114/T115 → T116/T117/T118 → T119 → T120/T121/T122/T123 → T124/T125)
        └─▶ Validation gate T126  ← MUST pass before Strong/Stretch
              ├─▶ Strong (T130, T131 → T132/T133 → T134)
              ├─▶ Stretch (T140, T141, T142)
              └─▶ Ship & Demo (T150 → T151/T152)
```

## Constitution Check (tasks level)

- Core isolation + signup/login precede Strong/Stretch (Art. I, VII) ✅
- Owner filter pushed into storage, not just routes (Art. X) — T111 ✅
- 404-not-403 for non-owned; 401 for no session (Art. X) — T116, T125 ✅
- No plaintext passwords/OTPs/tokens; env-only secrets (Art. X) — T100, T103, T110 ✅
- Blank SMTP/OAuth/JWT still runs locally (Art. VIII, IX) — T100, T102, T133 ✅
- Validation-on-real-data gate (Art. VIII) — T126 ✅
- Legacy data migrated, not dropped (Art. X data stewardship) — T112, T118 ✅

## Suggested sequencing
- **First:** T100–T103, T110–T112 (foundations + storage).
- **Then:** T113–T118 (backend auth + gating), T119–T123 (frontend), T124–T125 (tests).
- **Gate:** T126 on the real demo lecture.
- **Then Strong:** T130–T134. **Stretch only if Core+Strong are solid.**
