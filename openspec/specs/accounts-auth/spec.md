# accounts-auth

## Purpose

Provide user accounts and session authentication under `/api/auth/*`: email + 6-digit
OTP signup that sets a password, email/password login, server-verified Google sign-in,
and forgot/reset password. Passwords are bcrypt-hashed and sessions are stateless HS256
JWTs; OTPs and reset/verification tokens are stored only as sha256 hashes with short
TTLs, single use, and an attempt limit, so no plaintext secret is ever persisted or
returned (Constitution Art. X).

## Requirements

### Requirement: Email + OTP signup without account-existence disclosure

The system SHALL accept a signup request with an email, normalize it (trim + lowercase),
validate its format, and — unless the email already belongs to a verified local account
that has a password — create an unverified account if none exists and email a freshly
issued 6-digit OTP, while always returning the same neutral message regardless of whether
the account previously existed.

#### Scenario: New email starts signup

- **WHEN** `POST /api/auth/signup` is called with a valid, previously-unknown email
- **THEN** the system creates an unverified local user, issues a 6-digit OTP whose sha256
  hash (never the plaintext) is stored with the OTP TTL, and emails the OTP to the user
- **AND** the response is the neutral message "If that email can sign up, a verification code is on its way."

#### Scenario: Already-usable account is not re-issued a code

- **WHEN** `POST /api/auth/signup` is called for an email that already has a verified local
  account with a password hash
- **THEN** the system issues no new OTP and sends no email
- **AND** the response is the same neutral signup message, so the existing account is not disclosed

#### Scenario: Malformed email is rejected

- **WHEN** `POST /api/auth/signup` is called with an email that fails the format check
- **THEN** the system raises HTTP 400 with code `invalid_email`

### Requirement: OTP verification mints a single-use set-password token

The system SHALL verify the submitted OTP against the live (unused, unexpired) stored OTP
hash for the user, enforce the configured maximum attempts, mark the email verified on
success, consume the OTP, and return a single-use set-password token.

#### Scenario: Correct OTP verifies the email

- **WHEN** `POST /api/auth/verify-otp` is called with the matching OTP for a user whose
  stored OTP is unused and unexpired
- **THEN** the system marks the OTP used, sets `email_verified` true if not already, issues
  a set-password token (stored only as its hash, with the reset-token TTL), and returns
  `{set_password_token}`

#### Scenario: Wrong OTP increments attempts and is rejected

- **WHEN** `POST /api/auth/verify-otp` is called with an OTP whose hash does not match the stored hash
- **THEN** the system increments the stored token's attempt count and raises HTTP 400 with code `invalid_otp`

#### Scenario: Exhausted attempts lock the OTP out

- **WHEN** `POST /api/auth/verify-otp` is called and the stored OTP's attempts already reach
  the configured `otp_max_attempts`
- **THEN** the system marks the OTP used (locking it out) and raises HTTP 400 with code `invalid_otp`

#### Scenario: Expired, used, or unknown OTP is rejected

- **WHEN** `POST /api/auth/verify-otp` is called for an unknown email, or with a stored OTP
  that is already used or expired
- **THEN** the system raises HTTP 400 with code `invalid_otp` without revealing which condition failed

### Requirement: Set initial password and start a session

The system SHALL set the account's initial bcrypt password hash using a valid set-password
token, enforce the minimum password length, consume the token, and return a session token
plus the public user.

#### Scenario: Valid token sets the password and logs in

- **WHEN** `POST /api/auth/set-password` is called with a live set-password token and a
  password of at least 8 characters
- **THEN** the system stores the bcrypt hash of the password, sets `email_verified` true,
  marks the token used, and returns `{session_token, user}` where `user` carries no hash or token

#### Scenario: Weak password is rejected

- **WHEN** `POST /api/auth/set-password` is called with a password shorter than 8 characters
- **THEN** the system raises HTTP 400 with code `weak_password`

#### Scenario: Invalid or expired set-password token is rejected

- **WHEN** `POST /api/auth/set-password` is called with a token whose hash matches no live
  set-password token (missing, expired, or already used)
- **THEN** the system raises HTTP 400 with code `invalid_token`

### Requirement: Email/password login without enumeration

The system SHALL authenticate a normalized email and password by bcrypt-verifying against
the stored hash, returning a session token for verified accounts and using a single generic
error for both unknown email and wrong password.

#### Scenario: Valid credentials return a session

- **WHEN** `POST /api/auth/login` is called with an email and password that bcrypt-verify
  against the stored hash for a verified user
- **THEN** the system returns `{session_token, user}` with a freshly signed HS256 session JWT

#### Scenario: Unknown email or wrong password gives one generic error

- **WHEN** `POST /api/auth/login` is called with an unknown email, or with a known email but
  a password that fails bcrypt verification
- **THEN** the system raises HTTP 401 with code `invalid_credentials` in both cases identically

#### Scenario: Unverified account cannot log in

- **WHEN** `POST /api/auth/login` is called with a correct password for an account whose
  `email_verified` is false
- **THEN** the system raises HTTP 403 with code `email_not_verified`

### Requirement: Google sign-in verified server-side

The system SHALL accept a Google `id_token`, verify its RS256 signature against Google's
published JWKS via PyJWKClient, validate the audience against the configured OAuth client id
and the issuer against Google's issuers, and never trust account identity asserted by the
client; on success it finds-or-creates a verified user keyed by the Google `sub`.

#### Scenario: Valid Google token finds or creates a verified user

- **WHEN** `POST /api/auth/google` is called with an `id_token` whose signature, audience,
  and issuer verify and whose claims include `sub` and `email`
- **THEN** the system returns the user matching the `sub`, or links the `sub` (and marks
  verified) onto an existing same-email account, or creates a new verified Google-provider
  user, and returns `{session_token, user}`

#### Scenario: Google not configured

- **WHEN** `POST /api/auth/google` is called while the server has no `google_oauth_client_id`
- **THEN** the system raises HTTP 503 with code `google_not_configured`

#### Scenario: Invalid Google token is rejected

- **WHEN** `POST /api/auth/google` is called with a missing token or one that fails signature,
  audience, issuer, or required-claim verification
- **THEN** the system raises HTTP 400 with code `invalid_google_token`

### Requirement: Forgot and reset password

The system SHALL, on a forgot-password request, email a reset link containing a single-use
reset token only when the account exists while always returning the same neutral message,
and SHALL on reset set a new bcrypt password hash from a live reset token and consume it.

#### Scenario: Forgot-password emails a link only for existing accounts

- **WHEN** `POST /api/auth/forgot-password` is called with an email
- **THEN** the system, only if the account exists, issues a reset token (stored only as its
  hash, with the reset-token TTL) and emails a `frontend_url`-based `/reset-password?token=...` link
- **AND** the response is always the neutral message "If that account exists, a password reset link is on its way."

#### Scenario: Valid reset token sets a new password

- **WHEN** `POST /api/auth/reset-password` is called with a live reset token and a password
  of at least 8 characters
- **THEN** the system stores the new bcrypt hash, sets `email_verified` true, marks the token
  used, and returns `{ok: true}`

#### Scenario: Invalid or weak reset request is rejected

- **WHEN** `POST /api/auth/reset-password` is called with a password shorter than 8 characters,
  or with a token whose hash matches no live reset token
- **THEN** the system raises HTTP 400 with code `weak_password` or `invalid_token` respectively

### Requirement: Stateless session tokens resolve the current user

The system SHALL sign sessions as HS256 JWTs carrying `sub`, `type=session`, `iat`, and an
`exp` set by the configured expiry, and SHALL resolve the current user for protected routes
from an `Authorization: Bearer <jwt>` header, returning HTTP 401 for any missing, malformed,
invalid, expired, wrong-type, or now-deleted-user token.

#### Scenario: Valid bearer token returns the public user

- **WHEN** `GET /api/auth/me` is called with a valid, unexpired session bearer token whose
  user still exists
- **THEN** the system returns the public user (id, email, auth_provider, email_verified,
  created_at) with no password hash or token

#### Scenario: Missing or invalid token is unauthorized

- **WHEN** a protected route is called with no `Authorization` header, a non-bearer header,
  or a token that fails to decode, is expired, lacks `type=session`, or names a user that no longer exists
- **THEN** the system raises HTTP 401 with code `unauthorized`

### Requirement: Secrets are hashed at rest and one token per kind is active

The system SHALL never store or return plaintext passwords, OTPs, or tokens: passwords are
bcrypt-hashed over a sha256 pre-hash (avoiding bcrypt's 72-byte truncation), and OTPs/tokens
are stored only as sha256 hashes; issuing a new token of a given kind for a user SHALL
invalidate any prior token of that kind so only one is active.

#### Scenario: Issuing a token invalidates the prior one of the same kind

- **WHEN** a new OTP, set-password, or reset token is issued for a user
- **THEN** the system invalidates any existing token of that kind for the user before storing
  the sha256 hash of the new secret, leaving at most one active token of that kind

#### Scenario: Passwords are bcrypt-hashed over a sha256 pre-hash

- **WHEN** a password is stored
- **THEN** the system persists only a bcrypt hash computed over the base64 sha256 pre-hash of
  the password, so passwords longer than 72 bytes are not silently truncated and no plaintext is kept

### Requirement: Bootstrap admin account can be ensured

The system SHALL be able to ensure a bootstrap admin user exists for the configured
`bootstrap_admin_email`, creating it as a verified, password-less local account if missing
and otherwise returning the existing user, so single-tenant/legacy flows always bind to a
concrete owner.

#### Scenario: Bootstrap admin is created when absent

- **WHEN** `ensure_bootstrap_admin()` is called and no user exists for the normalized
  `bootstrap_admin_email`
- **THEN** the system creates a verified local user with no password hash and returns it

#### Scenario: Existing bootstrap admin is returned unchanged

- **WHEN** `ensure_bootstrap_admin()` is called and a user already exists for that email
- **THEN** the system returns the existing user without modifying it or issuing any credential

## Known deviations

- The bootstrap admin is created password-less and verified; it has no login credential until
  someone claims it via the forgot/reset-password flow. There is no admin-specific role or
  privilege modeled here — it exists only to give single-tenant/legacy flows a concrete owner.
- Google ID-token verification does not enforce token expiry or `email_verified` independently
  beyond what `jwt.decode` checks: `jwt.decode` validates `exp` (so expired tokens fail), but
  the returned `email_verified` claim is passed through and not required to be true before a
  Google account is treated as verified — Google sign-in always yields a verified user.
- `PyJWKClient` is a module-level singleton constructed on first Google sign-in and never reset;
  Google's JWKS is fetched/cached by that client with no explicit refresh handling in this code.
- The JWT signing key falls back to a hardcoded dev-only secret when `jwt_secret` is blank,
  logging a one-time warning. This keeps local dev runnable but is insecure if shipped without
  setting `JWT_SECRET`.
- Sessions are stateless JWTs with no server-side revocation or logout endpoint; a token remains
  valid until it expires (default 24h) even after password reset.
- Email format validation uses a permissive regex (`^[^@\s]+@[^@\s]+\.[^@\s]+$`) rather than a
  full validator, and email delivery falls back to console logging in dev (per `app/email.py`).
