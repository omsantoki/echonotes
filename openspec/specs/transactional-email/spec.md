# transactional-email

## Purpose

Deliver the two authentication-flow messages EchoNotes sends to users — the 6-digit signup verification (OTP) code and the password-reset link — over stdlib SMTP. When SMTP is not fully configured, or a send fails, the message is written to the server log instead so that local development needs no mail server and auth flows never break.

## Requirements

### Requirement: SMTP configured only when host, user, and password are all set

The system SHALL treat SMTP as configured only when the trimmed `smtp_host`, `smtp_user`, and `smtp_password` settings are all non-empty; if any one is blank the system SHALL NOT attempt to send over SMTP.

#### Scenario: All three credentials present

- **WHEN** `smtp_host`, `smtp_user`, and `smtp_password` are all set to non-blank values
- **THEN** SMTP is considered configured and the message is sent over SMTP

#### Scenario: One credential blank

- **WHEN** `smtp_host` is set but `smtp_user` or `smtp_password` is blank (or any one of the three is empty/whitespace)
- **THEN** SMTP is considered not configured
- **AND** the system does not attempt an SMTP send and uses the console-log fallback instead

### Requirement: Send plain-text email over SMTP when configured

The system SHALL, when SMTP is configured, build a plain-text `EmailMessage` and deliver it to the recipient via `smtplib.SMTP`, connecting to `smtp_host:smtp_port` with a 15-second timeout, attempting STARTTLS, logging in with `smtp_user`/`smtp_password`, and sending the message.

#### Scenario: Configured send

- **WHEN** `send_email(to, subject, body)` is called and SMTP is configured
- **THEN** a connection is opened to `smtp_host` on `smtp_port` with a 15-second timeout
- **AND** the message is sent with `From` set to `smtp_from` when present (otherwise `smtp_user`), `To` set to the recipient, the given `Subject`, and the body as plain text

#### Scenario: STARTTLS unsupported by server

- **WHEN** the SMTP server does not support STARTTLS and raises `SMTPException` during `starttls()`
- **THEN** the failure is swallowed and the send proceeds without TLS (e.g. a localhost test relay)

### Requirement: Fall back to the server log on any send failure

The system SHALL catch any exception raised during the SMTP send, log it at error level (without exposing credentials), and fall through to writing the message to the server log so the recipient can still proceed.

#### Scenario: SMTP send raises

- **WHEN** SMTP is configured but the send raises an exception (e.g. connection refused, login failure)
- **THEN** the error is logged at error level identifying the recipient and the exception
- **AND** the full message (subject and body) is written to the server log as the fallback

### Requirement: Console-log fallback carries the message body

The system SHALL, when SMTP is not configured or a send fails, write a warning-level `[email:console]` log line containing the recipient, subject, and full body — which includes the OTP code or reset link — so local development requires no mail server.

#### Scenario: Unconfigured local dev

- **WHEN** `send_email` is called with SMTP not configured (blank credentials)
- **THEN** a warning-level log line prefixed `[email:console]` is emitted containing the recipient, subject, and body
- **AND** the OTP code or reset link embedded in the body is readable from the server log

### Requirement: Sending never raises into the auth flow

The system SHALL ensure `send_email` (and the `send_otp_email` / `send_reset_email` helpers built on it) never raise; a mail-server problem MUST NOT cause the calling signup or forgot-password flow to fail.

#### Scenario: Mail server hiccup during signup

- **WHEN** an auth flow calls `send_otp_email` or `send_reset_email` and the SMTP send fails
- **THEN** no exception propagates to the caller
- **AND** the auth flow completes using the console-log fallback

### Requirement: Compose the signup OTP email

The system SHALL provide `send_otp_email(to, otp)` that sends a message with subject "Your EchoNotes verification code" whose body contains the verification code and states that it expires in `otp_ttl` minutes (the seconds setting divided by 60).

#### Scenario: OTP email composed

- **WHEN** `send_otp_email(to, otp)` is called
- **THEN** an email is sent (or logged) with the fixed verification-code subject
- **AND** the body contains the OTP value and an expiry stated in minutes derived from `otp_ttl`

### Requirement: Compose the password-reset email

The system SHALL provide `send_reset_email(to, reset_url)` that sends a message with subject "Reset your EchoNotes password" whose body contains the reset link and states that it expires in `reset_token_ttl` minutes (the seconds setting divided by 60).

#### Scenario: Reset email composed

- **WHEN** `send_reset_email(to, reset_url)` is called
- **THEN** an email is sent (or logged) with the fixed password-reset subject
- **AND** the body contains the `reset_url` and an expiry stated in minutes derived from `reset_token_ttl`

## Known deviations

- The console-log fallback deliberately prints the OTP code and reset link in clear text to the server log. This is the single intentional exception to the project's secret-hygiene rule (no plaintext secrets in logs); it exists so local development needs no mail server and so an incomplete or failing SMTP setup does not strand the user. SMTP credentials themselves are never logged — only the message body is.
- Failure handling is coarse: every exception from the SMTP block (connection, STARTTLS handshake outside the swallowed `SMTPException`, login, send) is caught by a single broad `except Exception`, logged, and treated identically as "fall back to console." There is no retry, queue, or per-error distinction.
- Emails are plain text only; there is no HTML alternative, multipart body, or templating beyond the inline f-strings.
- STARTTLS is best-effort: if the server does not advertise/support it the message is sent over an unencrypted connection. There is no `smtp_ssl` / implicit-TLS path and no setting to require TLS.
- The configured-send path returns early on success; there is no return value or status surfaced to the caller indicating whether delivery used SMTP or the console fallback.
