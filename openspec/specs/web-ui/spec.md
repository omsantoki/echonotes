# web-ui

## Purpose

Deliver the EchoNotes product surface as a React + Vite single-page app (public landing,
auth flows, per-user course library, lecture upload, and merged-document reading) that talks
to the backend over the JSON API only, with the merged source-labeled document as the star;
plus a minimal single-tenant server-rendered fallback (`app/web.py`) that reuses the same
ingestion path. Auth context + a `RequireAuth` guard gate the data pages, the Google button
self-hides when Google is unconfigured, and theme is bootstrapped before first paint.

## Requirements

### Requirement: Public landing with gated data routes

The SPA SHALL keep the landing page (`/`) and the auth pages (`/login`, `/signup`,
`/forgot-password`, `/reset-password`) public, and SHALL wrap the data routes (`/app`,
`/courses/:courseId`, `/courses/:courseId/upload`, `/lectures/:lectureId`) behind a
`RequireAuth` guard that redirects unauthenticated visitors to `/login` while preserving the
intended destination, and that renders a spinner (not a redirect) while the initial session
bootstrap is still in flight.

#### Scenario: Unauthenticated visitor opens a data route

- **WHEN** a visitor with no valid session navigates to a gated route such as `/app` after the
  auth bootstrap has finished
- **THEN** the guard SHALL redirect (replace) to `/login` with `state.from` set to the
  attempted location so login can return the user there

#### Scenario: Auth bootstrap still loading

- **WHEN** a gated route is rendered while `loading` is true (the initial `/me` check is in flight)
- **THEN** the guard SHALL render a centered spinner and SHALL NOT redirect

#### Scenario: Landing page stays public

- **WHEN** an unauthenticated visitor opens `/`
- **THEN** the landing page SHALL render without forcing a login
- **AND** an authenticated visitor's landing CTAs SHALL link to `/app` instead of `/signup`

### Requirement: Session bootstrap and JWT-backed auth context

The SPA SHALL persist the session JWT in `localStorage` and, on load when a token exists,
confirm it via `GET /api/auth/me`; it SHALL drop the session only on a genuine 401 (keeping
the token through network/backend hiccups), SHALL clear the React Query cache on sign-in and
sign-out so no previous user's data is shown, and SHALL react to out-of-band token clears by
dropping the current user.

#### Scenario: Valid token confirmed on load

- **WHEN** the app loads with a stored session token
- **THEN** the auth context SHALL call `/api/auth/me`, set the returned `user`, and finish with
  `loading` false and `isAuthenticated` true

#### Scenario: Expired token rejected on load

- **WHEN** the `/me` bootstrap fails with an `ApiRequestError` whose status is 401
- **THEN** the stored token SHALL be cleared so the guard sends the user to `/login`

#### Scenario: Transient failure does not log the user out

- **WHEN** the `/me` bootstrap fails with a non-401 error (network blip or backend hiccup)
- **THEN** the token SHALL be kept so a reload can recover, and the user SHALL NOT be forcibly logged out

#### Scenario: Sign-in and sign-out reset cached tenant data

- **WHEN** `signIn` or `signOut` runs
- **THEN** the React Query cache SHALL be cleared so a different account never sees the prior
  account's cached courses or lectures

### Requirement: JSON-API data access with 401 session handling

The SPA SHALL reach the backend exclusively through the typed `lib/http` + `lib/api`
client, attaching `Authorization: Bearer <jwt>` on every request when a token is present, and
SHALL treat a 401 on a non-`/api/auth/*` path as session expiry by clearing the token so the
guards redirect to `/login`; a 401 on an `/api/auth/*` path SHALL instead surface inline as an
`ApiRequestError` and SHALL NOT clear the session.

#### Scenario: Authenticated request carries the bearer token

- **WHEN** any data request is made through `getJson`/`postJson`/`del` while a token is stored
- **THEN** the request SHALL include the `Authorization: Bearer <token>` header

#### Scenario: 401 on a data route clears the session

- **WHEN** a data request to a non-`/api/auth/*` path returns HTTP 401
- **THEN** the client SHALL clear the stored token before throwing the `ApiRequestError`

#### Scenario: 401 on an auth route is surfaced, not cleared

- **WHEN** a request to an `/api/auth/*` path (e.g. a bad login) returns HTTP 401
- **THEN** the client SHALL NOT clear the session and SHALL throw an `ApiRequestError` whose
  `code`/`message` come from the JSON error body when present

### Requirement: Account auth flows

The SPA SHALL provide login, multi-step signup (email then 6-digit OTP then password),
forgot-password, and reset-password flows that call the corresponding `/api/auth/*` endpoints,
persist the returned session on success, surface inline errors, and keep account-existence
neutral by advancing/confirming regardless of whether an account exists.

#### Scenario: Successful email/password login

- **WHEN** the login form is submitted with credentials that the API accepts
- **THEN** the SPA SHALL store the returned `session_token` + `user` and navigate to the saved
  destination (`state.from`) or `/app`

#### Scenario: Signup walks email then code then password

- **WHEN** the user submits their email, then the 6-digit code, then a matching password
- **THEN** the SPA SHALL call `/api/auth/signup`, `/api/auth/verify-otp`, and
  `/api/auth/set-password` in turn, advancing to OTP entry even on a neutral signup response,
  and SHALL sign the user in and navigate to `/app` after the password is set

#### Scenario: Password confirmation must match

- **WHEN** the signup password step or reset-password form is submitted with mismatched
  password and confirm fields
- **THEN** the SPA SHALL show "Passwords do not match." and SHALL NOT call the API

#### Scenario: Forgot-password gives a neutral response

- **WHEN** the forgot-password form is submitted
- **THEN** the SPA SHALL call `/api/auth/forgot-password` and show a neutral "if an account
  exists" confirmation without disclosing whether the email is registered

#### Scenario: Reset link missing its token

- **WHEN** `/reset-password` is opened without a `token` query parameter
- **THEN** the SPA SHALL show an "Invalid reset link" message linking back to forgot-password
  instead of the new-password form

### Requirement: Google sign-in self-hides when unconfigured

The SPA SHALL render the Google Identity Services button only when `VITE_GOOGLE_CLIENT_ID`
is set, loading the GIS script lazily and exchanging the returned credential via
`POST /api/auth/google`; when the client id is blank the component SHALL render nothing so
local dev needs no Google setup.

#### Scenario: Google client id configured

- **WHEN** a client id is present and the GIS script loads
- **THEN** the SPA SHALL render the Google button and, on a returned credential, call
  `/api/auth/google` and sign the user in on success

#### Scenario: Google not configured

- **WHEN** `VITE_GOOGLE_CLIENT_ID` is blank
- **THEN** the Google button component SHALL render nothing (no button, no divider)

### Requirement: Course library and lecture upload

The SPA SHALL list the signed-in user's courses at `/app`, let them create and delete courses,
open a course's lectures and cross-lecture search at `/courses/:courseId`, and upload a
lecture's audio + slides at `/courses/:courseId/upload` via a progress-reporting multipart
request, validating file type/size client-side before sending.

#### Scenario: My courses lists the user's own courses

- **WHEN** an authenticated user opens `/app`
- **THEN** the SPA SHALL fetch `GET /api/courses` and render the courses, an empty state when
  there are none, and a create-course action

#### Scenario: Upload validates files before sending

- **WHEN** the upload form is submitted with a missing title, an unsupported audio extension,
  a non-PDF slides file, or a file over 500 MB
- **THEN** the SPA SHALL show the relevant field error and SHALL NOT start the upload

#### Scenario: Successful upload navigates to the reading page

- **WHEN** a valid upload completes with a 202 accepted response
- **THEN** the SPA SHALL seed the lecture query cache as `processing`, invalidate the course +
  courses queries, and navigate to `/lectures/:lectureId`

#### Scenario: Deleting a course confirms then returns home

- **WHEN** the user confirms deleting a course
- **THEN** the SPA SHALL call `DELETE /api/courses/:id`, drop its cached queries, and navigate to `/app`

### Requirement: Lecture reading with live processing and the merged document as the star

The SPA SHALL render the lecture reading page from `GET /api/lectures/:id`, polling every 2s
while the status is `uploaded`/`processing` and stopping at a terminal state or error; it SHALL
show a staged processing tracker while composing, an error state on failure, and — when
`ready` — the merged source-labeled document with spoken-only highlights, a table of contents,
and Markdown/HTML export links.

#### Scenario: Polling while processing

- **WHEN** a lecture's status is `uploaded` or `processing`
- **THEN** the SPA SHALL refetch every 2000ms and render the staged `ProcessingTracker` driven
  by the backend progress string, and SHALL stop polling once the status becomes `ready` or `failed`

#### Scenario: Terminal client error stops polling

- **WHEN** the lecture query errors with a 4xx (e.g. 404 not-found / not-owned)
- **THEN** the SPA SHALL not retry the 4xx and SHALL stop the polling interval

#### Scenario: Ready lecture shows the merged document

- **WHEN** the lecture status is `ready`
- **THEN** the SPA SHALL render the merged document with the source legend, spoken-only insights
  highlighted (★) with a "why" reason, a table of contents, and Markdown + HTML export links to
  `/api/lectures/:id/export`

#### Scenario: Failed lecture shows an error with delete

- **WHEN** the lecture status is `failed`
- **THEN** the SPA SHALL show an error state (stripping a leading "Failed:" from the progress)
  with a delete action and a link back to courses

### Requirement: Theme with no-flash bootstrap

The web UI SHALL resolve the active theme from the persisted `echonotes-theme` value or the
OS `prefers-color-scheme`, apply the `dark` class to the document element before first paint via
an inline script in `index.html`, and expose a toggle that persists the chosen theme.

#### Scenario: Dark preference applied before paint

- **WHEN** the page loads with a stored `dark` theme or no stored theme but a dark OS preference
- **THEN** the inline bootstrap script SHALL add the `dark` class to `<html>` before React mounts,
  avoiding a flash of the wrong theme

#### Scenario: Toggle persists the theme

- **WHEN** the user toggles the theme
- **THEN** the SPA SHALL switch between `light` and `dark`, apply the `dark` class accordingly,
  and persist the choice under `echonotes-theme`

### Requirement: Single-tenant server-rendered fallback console

The backend SHALL serve a minimal HTML console under `app/web.py` that operates as the
bootstrap admin owner, letting that owner create courses, upload a lecture (audio + slides) via a
multipart form into the same ingestion path as the JSON API, auto-refresh while a lecture is
processing, search a course, and read/export the merged document; it SHALL return owner-scoped
404 HTML pages for courses/lectures the admin does not own.

#### Scenario: Owner-scoped course listing and creation

- **WHEN** the server-rendered home (`GET /`) is requested
- **THEN** it SHALL list only the bootstrap admin's courses and render forms to create a course
  (`POST /web/courses`) and upload a lecture (`POST /web/lectures`), redirecting with 303 after each

#### Scenario: Processing lecture auto-refreshes

- **WHEN** a lecture page is requested while its status is `processing`
- **THEN** the page SHALL include a `<meta http-equiv="refresh" content="3">` so progress updates
  without a manual reload

#### Scenario: Ready lecture renders the merged document with export links

- **WHEN** a lecture page is requested for a `ready` lecture owned by the admin
- **THEN** it SHALL render the merged document HTML plus Markdown and HTML export links to
  `/api/lectures/{id}/export`

#### Scenario: Non-owned or missing course returns 404

- **WHEN** a course or lecture id that the bootstrap admin does not own is requested
- **THEN** the server SHALL respond with a 404 HTML "not found" page (never another user's data)

## Known deviations

- The SPA ships a `HomePage` at `/app` ("My courses") that overlaps conceptually with the
  marketing `LandingPage` at `/`; both exist and are wired into the router. There is no separate
  legacy home being removed — both pages are live.
- `lib/assets.ts` (`resolveAssetUrl`) and the `image_ref` field on diagram segments support
  rendering preserved diagram images from `/assets/...`; whether images actually display depends
  on the backend asset route and is out of scope for this UI capability.
- The `googleEnabled` export in `GoogleButton.tsx` is computed but not consumed elsewhere; the
  button hides itself by returning `null`, so the export is effectively dead code today.
- The XHR upload path in `lib/api.ts` duplicates the bearer-token attachment and 401-clear logic
  from `lib/http.ts` because `fetch` cannot report upload progress; the two paths must be kept in
  sync by hand.
- The server-rendered console (`app/web.py`) is explicitly single-tenant (always the bootstrap
  admin) and is not the multi-tenant product surface; it has no login UI and relies on
  `ensure_bootstrap_admin()`. It is described in the code as tasks T019/T021/T031 and reuses the
  JSON ingestion path rather than a second pipeline.
- Spoken-only detection in the reading page tolerates older data by also matching a `reason`
  string containing "★ Spoken-only" in addition to the structured `spoken_only` flag.
