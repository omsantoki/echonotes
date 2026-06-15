# Quickstart: Accounts & Multi-Tenancy

<!-- Spec Kit artifact: specs/002-accounts-multitenancy/quickstart.md
Extends ../001-echonotes-core/quickstart.md. The whole flow runs locally with
SMTP/OAuth/JWT env BLANK — email prints to the server log, the Google button is
hidden, and a dev JWT secret is used. -->

> Confirm current versions before installing (see research.md). This build uses
> PyJWT 2.13.0 (`PyJWT[crypto]`) + bcrypt 5.0.0; email is stdlib `smtplib`.

## Prerequisites
- The 001 prerequisites (Python 3.11+, the chosen provider for transcribe/embed/merge).
- `pip install -r requirements.txt` (now includes `PyJWT[crypto]`, `bcrypt`).

## Env (all blank = local dev still works)
Add to `backend/.env` (see `.env.example`); leaving these blank keeps local dev fully working:
```bash
JWT_SECRET=                       # blank → a dev-only default is used (set a real secret in prod)
JWT_EXPIRY=86400                  # session lifetime, seconds
OTP_TTL=600                       # OTP lifetime, seconds (~10 min)
OTP_MAX_ATTEMPTS=5
RESET_TOKEN_TTL=3600              # set-password / reset link lifetime, seconds
FRONTEND_URL=http://localhost:5173  # base for reset links in emails
BOOTSTRAP_ADMIN_EMAIL=admin@echonotes.local

# SMTP — blank = OTP / reset links print to the server log (no mail server needed)
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=                    # Gmail: an App Password (never your real password)
SMTP_FROM=

# Google sign-in — blank = the "Continue with Google" button is hidden / no-ops
GOOGLE_OAUTH_CLIENT_ID=
```
Frontend (`frontend/.env`): set `VITE_GOOGLE_CLIENT_ID=` (blank hides the Google button).

## Migrate existing "common" courses (run once)
```bash
# from backend/
python scripts/init_db.py            # prod only: adds users, auth_tokens, courses.owner_id
python scripts/migrate_add_owner.py  # ensures the bootstrap admin + assigns ownerless courses to it
```
Local dev (registry.json) only needs `migrate_add_owner.py`. To claim the migrated legacy library,
run forgot-password against `BOOTSTRAP_ADMIN_EMAIL` and use the reset link printed in the log.

## Run the full flow locally (console email)
```bash
# from backend/
uvicorn app.main:app --reload
# in another terminal: cd frontend && npm run dev
```
1. Visit `http://localhost:5173/` — the landing page renders, **no login wall**; a **Log in / Sign up**
   control sits in the header corner.
2. Sign up with an email → watch the server log for the **6-digit OTP** → enter it → set a password →
   you land in the app with **zero courses**.
3. Create a course, upload the demo lecture (backend/samples/); it processes end-to-end, owned by you.
4. Log out, sign up as a **second** user → you see **none** of the first user's courses; pasting the
   first user's course URL returns 404.
5. Forgot password → reset link printed in the log → open it → set a new password → log in.

## Privacy / isolation check (Art. X)
- As user B, `GET /api/courses` lists only B's courses; `GET /api/courses/{A's id}` → 404; no session → 401.
- The server log shows OTPs/reset links in dev, but no password, hash, or token is ever stored in plaintext.

## Deploy
- Set `JWT_SECRET` to a strong random value; configure SMTP (or accept console email); set
  `GOOGLE_OAUTH_CLIENT_ID` + frontend `VITE_GOOGLE_CLIENT_ID` for Google sign-in; set `FRONTEND_URL`.
- Run `init_db.py` then `migrate_add_owner.py` against the managed Postgres once.
