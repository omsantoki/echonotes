# Feature Specification: Accounts & Multi-Tenancy

<!--
Spec Kit artifact: specs/002-accounts-multitenancy/spec.md
Output of the /speckit.specify step. Focuses on WHAT and WHY — no tech stack,
no implementation detail (those live in plan.md). Written to satisfy the
constitution in .specify/memory/constitution.md (esp. the new Article X).

Builds on 001-echonotes-core: this feature adds an OWNER to every course and
gates every data route behind an authenticated session. See
specs/001-echonotes-core/{data-model.md,contracts/api.md} for the updated
ownership rules cross-referenced here.
-->

**Feature branch:** `002-accounts-multitenancy`
**Status:** Draft → Ready for `/speckit.plan`
**Owner:** Om Santoki (202301019)
**Depends on:** `001-echonotes-core` (Course/Lecture/NoteChunk; per-course persistence)

---

## 1. Summary

EchoNotes today is single-tenant: every course is global ("common") and anyone
who reaches the app sees everything. This feature makes EchoNotes **multi-user**.
Each person **signs up** (email + password, verified by an emailed one-time code),
**logs in**, and **owns their own courses, lectures, notes, diagrams and search** —
and can never see, search, open, or delete anyone else's data.

Authentication is **not forced on arrival**: the public landing page (`/`) still
renders for everyone, with a small **Log in / Sign up** control in the corner of
the app header. Only the *data* pages (courses, lectures, upload, search) require
a session. The product's core — merged, source-labeled notes (001) — is unchanged;
it now runs inside a per-user boundary.

## 2. Problem Statement

Two problems block real use beyond a single demo:

1. **No identity.** There is no notion of "me." Notes a student spent effort on
   are mixed into one global pile with everyone else's; there is no private,
   personal, persistent library — the very thing Constitution Art. V promises.
2. **No isolation.** Because every course is "common," one student's lecture notes
   are visible (and deletable) by any other visitor. That is unacceptable for a
   tool meant to hold a student's coursework across a semester.

Solving these unlocks the adoption persona (a class, a department) without changing
the core value: it just makes the per-course library *belong to someone*.

## 3. Goals

- Let a user create an account with **email + password**, proving the email with a
  **6-digit OTP** before any password is set.
- Let a user **log in** with email + password and stay signed in via a session token.
- Offer **"Continue with Google"** as an alternative sign-in.
- Offer **forgot-password → emailed reset link → reset** for account recovery.
- **Isolate every tenant:** a user only ever reads/lists/searches/deletes their own
  courses, lectures, notes, and diagrams (Constitution Art. X).
- Keep the **landing page public**; gate only the data pages, with a corner CTA.
- **Migrate** existing "common" courses to a bootstrap owner — never drop data.
- Keep **local dev runnable with zero external services** (blank SMTP/OAuth/JWT env).

## 4. Non-Goals

- Not building organizations / teams / shared courses (each course has exactly one
  owner). Sharing is out of scope for this feature.
- Not building roles/permissions beyond "owner of my data" + a bootstrap admin.
- Not building social logins beyond Google (no Apple/GitHub/etc. this round).
- Not building 2FA/TOTP, magic-link passwordless login, or SSO/SAML.
- Not building an admin console for managing other users' data.
- Not changing the 001 pipeline, merge quality, or "store notes not audio" rule.

## 5. User Personas

- **Aarav, the returning student (primary):** signs up once, then comes back each
  week to add lectures to *his* courses; expects last week's notes to be there and
  private.
- **Diya, the classmate (secondary):** uses the same deployed instance; must never
  see Aarav's courses, and he must never see hers.
- **Course rep / department (adoption):** wants many students on one deployment,
  each with an isolated library — the precondition for institutional adoption.
- **Returning user who forgot their password (recovery):** needs a safe path back in
  without contacting support.

## 6. User Stories & Acceptance Criteria

### US-8 (Core) — Sign up and verify my email
*As a new user, I sign up with my email, prove I own it with a code, and set a password.*

**Acceptance:**
- GIVEN I enter an email on the sign-up page, WHEN I submit, THEN the system creates
  an **unverified** account and emails me a **6-digit code** (shown in the server log
  in local dev). The response never reveals whether the email already existed.
- GIVEN I enter the correct code before it expires, WHEN I submit it, THEN my email is
  marked verified and I receive a short-lived token to set my password.
- GIVEN a verified email + that token, WHEN I set a password, THEN my account is usable
  and I am logged in (I receive a session token) and land in the app with **zero courses**.
- GIVEN a wrong code, WHEN I submit it, THEN I am told it is incorrect; after too many
  attempts or once expired, the code stops working and I can request a new one.

### US-9 (Core) — Log in and stay signed in
*As a returning user, I log in with email + password and reach my own courses.*

**Acceptance:**
- GIVEN a verified account, WHEN I submit the right email + password, THEN I receive a
  session token and reach my courses.
- GIVEN wrong credentials, THEN I get a generic "invalid email or password" (no hint
  about which was wrong, and no leak of whether the email exists).
- GIVEN an **unverified** account, WHEN I try to log in, THEN I am told to verify my
  email first and am NOT issued a session.
- GIVEN a valid session token, WHEN I reload the app, THEN I remain signed in until the
  token expires or I log out.

### US-10 (Core) — My data is mine alone
*As a user, I only ever see my own courses, lectures, notes, diagrams and search results.*

**Acceptance:**
- GIVEN two users A and B, WHEN B lists courses, THEN B sees only B's courses (none of A's).
- GIVEN a course owned by A, WHEN B opens its URL / fetches it / searches it / deletes it /
  uploads to it, THEN B receives **404 Not Found** (existence is not leaked; not 403).
- GIVEN a lecture owned by A, WHEN B opens / exports / deletes it, THEN B receives 404.
- GIVEN no session at all, WHEN any data route is called, THEN it returns **401 Unauthorized**.
- AND search results for a course only ever span that course's (the owner's) lectures.

### US-11 (Core) — The landing page is open; the app is gated
*As a visitor, I can read the marketing landing page without logging in.*

**Acceptance:**
- GIVEN I am logged out, WHEN I visit `/`, THEN the landing page renders fully with **no
  forced login**, and a small **Log in / Sign up** control is visible in the header corner.
- GIVEN I am logged out, WHEN I navigate to a data page (`/app`, a course, upload, a lecture),
  THEN I am redirected to `/login`, and after logging in I land on the page I intended.
- GIVEN I am logged in, WHEN I view the header, THEN it shows my email and a **Log out** action.

### US-12 (Strong) — Recover a forgotten password
*As a user who forgot my password, I request a reset link by email and choose a new password.*

**Acceptance:**
- GIVEN I submit my email on the forgot-password page, THEN I always see the same "if that
  email exists, a link is on its way" message (no leak of which emails exist), and if the
  account exists a reset link is emailed (printed to the log in local dev).
- GIVEN I open a valid, unexpired reset link and set a new password, THEN the link is
  consumed (single-use), my password is updated, and I can log in with it.
- GIVEN an expired or already-used link, WHEN I try to reset, THEN I am told the link is no
  longer valid and asked to request a new one.

### US-13 (Strong) — Continue with Google
*As a user, I sign in with my Google account in one click.*

**Acceptance:**
- GIVEN I click "Continue with Google" and complete Google's prompt, THEN the system verifies
  the Google token server-side and, if it is my first time, creates a verified account linked
  to my Google identity; otherwise it logs me into my existing account.
- AND a Google-only account has no password but can still use forgot-password to add one.
- AND if Google sign-in is not configured on the server, the button is hidden / no-ops cleanly.

### US-14 (Stretch) — Account hygiene
*As a user, I get sensible protection and can manage my session.*

**Acceptance (any subset, only if Core+Strong are solid):**
- Repeated failed logins / OTP attempts are rate-limited or briefly locked out.
- Session tokens can be refreshed/rotated rather than forcing a hard re-login at expiry.
- An account-settings page lets me change my password and see my email/provider.

## 7. Functional Requirements

> FR numbering continues the project sequence (001 ended at FR-13). Each traces to a
> task in tasks.md. Tiers follow Constitution Art. VII.

**Accounts — signup, OTP, password (Core)**
- **FR-14:** Accept a signup `{email}`; normalize email to lowercase; create an
  **unverified** user; never reveal whether the email already existed.
- **FR-15:** Generate a **6-digit OTP**, store it **hashed** with a short TTL (~10 min),
  attempt-limited, and email it (console fallback in local dev). Never store/log it in plaintext.
- **FR-16:** Verify `{email, otp}`: on success mark the email verified and issue a short-lived,
  single-use **set-password token**; on failure count the attempt and reject once over the limit
  or expired.
- **FR-17:** Accept `{token, password}` to set the password (hashed with a vetted hasher),
  consume the token, and issue a **session token**.

**Login & session (Core)**
- **FR-18:** Accept `{email, password}`; on match for a **verified** account issue a session
  token; reject unverified accounts; return a generic error on bad credentials (no email-existence
  or which-field leak).
- **FR-19:** Provide `GET /api/auth/me` returning the current user from the session token; an
  invalid/expired/absent token yields 401.
- **FR-20:** Session tokens are signed with an expiry; the secret comes from env only.

**Tenant isolation (Core)**
- **FR-21:** Every course has an **owner** (`owner_id`). New courses are owned by their creator.
- **FR-22:** Gate **all** course/lecture/search/upload/delete routes behind an authenticated user;
  no session → **401**.
- **FR-23:** Scope every read/list/query/delete to the caller: listing returns only the user's
  courses; fetching/searching/deleting/uploading-to a course or lecture the user does not own
  returns **404** (not 403), so existence is not leaked. The owner filter is enforced in the
  storage layer, not only the route.
- **FR-24:** Cross-lecture search and "builds-on" retrieval never cross a course the user cannot
  access (course access is already owner-gated; assert it for defense-in-depth).
- **FR-25:** Migrate existing ownerless ("common") courses to a single **bootstrap owner** —
  document the mapping; never silently drop data.

**Google sign-in (Strong)**
- **FR-26:** Accept a Google `{id_token}`, verify it **server-side against Google's certs**
  (audience = configured client id; never trust the client), then find-or-create a **verified**
  user linked by `google_sub`, and issue a session token.

**Forgot / reset password (Strong)**
- **FR-27:** Accept `{email}` for forgot-password; always respond 200 with a neutral message;
  if the account exists, email a reset **link** carrying a hashed, short-TTL, single-use token.
- **FR-28:** Accept `{token, password}` to set a new password and invalidate the reset token
  (single-use; expired/used tokens are rejected).

**Email & secrets (Core, cross-cutting)**
- **FR-29:** Send transactional email (OTP, reset link) via SMTP; if SMTP env is blank, fall
  back to printing the OTP / link to the server log so local dev needs no mail server.
- **FR-30:** No plaintext passwords, OTPs, or tokens are ever stored or logged; all secrets
  (JWT secret, SMTP creds, Google client id) come from env with safe blank dev defaults
  (Constitution Art. X).

**Stretch**
- **FR-31 (Stretch):** Refresh-token rotation; rate-limit / lockout polish; an account-settings
  page (change password; view email/provider).

## 8. Non-Functional Requirements

- **Privacy / isolation (Art. X):** a user's data is never observable by another user; cross-tenant
  probes return 404, not 403.
- **Secret hygiene (Art. X):** passwords/OTPs/tokens hashed at rest; secrets via env only; nothing
  secret in logs or responses.
- **Local-first (Art. VIII, IX):** the whole app — including signup/OTP/reset — runs with blank
  SMTP/OAuth/JWT env (console email, dev JWT secret, Google button hidden).
- **Continuity preserved (Art. V):** per-course persistence is unchanged; it is now per-*user*-per-course.
- **No theater (Art. II):** auth does real work (verified email, hashed secrets, server-side Google
  verification); we don't fake it.

## 9. Key Edge Cases & Risks

- **Email-existence leakage** via signup / forgot-password / login error wording → uniform responses (FR-14, FR-18, FR-27).
- **403-vs-404 leakage** of others' resources → always 404 for non-owned (FR-23).
- **OTP brute force** → 6 digits + short TTL + attempt limit + single active code (FR-15, FR-16).
- **Token reuse / replay** → verify/reset/set-password tokens are single-use, hashed, short-TTL (FR-16, FR-17, FR-28).
- **Google token spoofing** → verify signature + audience + issuer server-side against Google certs (FR-26).
- **Legacy data orphaned** by the owner change → bootstrap-owner migration, documented (FR-25).
- **Local dev blocked** by missing mail/OAuth → graceful console/no-op fallbacks (FR-29, FR-26).
- **bcrypt 72-byte truncation** → pre-hash the password before bcrypt (see data-model.md).

## 10. Success Metrics (for the demo & judging)

- Two users on the same deployment, each with a private library; user B's direct URL to user A's
  course returns 404.
- A new user signs up, verifies via the OTP printed in the log, sets a password, and processes the
  real demo lecture (backend/samples/) into notes owned by them.
- Forgot-password produces a working reset link (in the log) that lets the user log in again.
- "Continue with Google" creates/logs in a user when configured.
- Local dev still boots and completes the whole flow with every cloud/SMTP/OAuth env var blank.

## 11. [NEEDS CLARIFICATION] — resolved (see research.md)

- Password hasher: **bcrypt** (already vetted/available) with a sha256 pre-hash for the 72-byte limit.
- Session mechanism: **stateless JWT** (HS256) with expiry; refresh rotation is Stretch.
- Google verification: **PyJWT `PyJWKClient`** against Google's JWKS (no extra google-auth dep).
- Bootstrap owner for legacy courses: a single admin user (`BOOTSTRAP_ADMIN_EMAIL`), assigned by a
  one-shot migration script.
