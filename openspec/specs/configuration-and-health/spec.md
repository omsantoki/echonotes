# configuration-and-health

## Purpose

Centralize all configuration in one environment-driven settings object (`app/config.py`) with safe blank/dev defaults so local development runs with zero external services, and expose an operator-facing `/api/health` endpoint plus a uniform error envelope (`app/main.py`) that reveal which backend each subsystem resolved to and whether each secret is set — never the secret value itself.

## Requirements

### Requirement: Settings loaded from environment with safe defaults

The system SHALL load all configuration through a single `pydantic_settings.BaseSettings` subclass (`Settings`) that reads from environment variables and an optional `.env` file, ignoring unknown keys, and SHALL default every external-service credential and URL to a blank/dev value so the app starts with no external services configured.

#### Scenario: Local dev with nothing configured

- **WHEN** the app starts with no `.env` and no relevant environment variables set
- **THEN** `provider` defaults to `"local"`, all cloud backend vars (`qdrant_url`, `chroma_http_url`, `database_url`, `s3_bucket`) default to `""`, and `jwt_secret`/`smtp_host`/`google_oauth_client_id` default to `""`
- **AND** the app constructs `Settings` successfully and runs without contacting any external service

#### Scenario: Environment overrides a default

- **WHEN** an environment variable (e.g. `PROVIDER` or `DATABASE_URL`) is set
- **THEN** the matching `Settings` field takes that value, overriding the in-code default
- **AND** unknown environment keys are ignored (`extra="ignore"`)

#### Scenario: Cached single instance

- **WHEN** code calls `get_settings()`
- **THEN** it returns an `lru_cache`d `Settings` instance, so all callers share one configuration object loaded once per process

### Requirement: Active embedding model resolved from provider

The system SHALL resolve the one embedding model in force via `active_embedding_model()`, returning `local_embedding_model` when `provider == "local"` and `embedding_model` otherwise.

#### Scenario: Local provider

- **WHEN** `provider` is `"local"`
- **THEN** `active_embedding_model()` returns `local_embedding_model` (default `all-MiniLM-L6-v2`)

#### Scenario: Non-local provider

- **WHEN** `provider` is not `"local"` (e.g. `"openai"`)
- **THEN** `active_embedding_model()` returns `embedding_model` (default `text-embedding-3-small`)

### Requirement: Storage backend resolution surfaced without credentials

The system SHALL resolve each storage subsystem to a named backend via `active_storage()` based solely on whether the relevant env var is set: vectors to `"qdrant"` if `qdrant_url` is set, else `"chroma-remote"` if `chroma_http_url` is set, else `"chroma-local"`; registry to `"postgres"` if `database_url` is set, else `"json"`; objects to `"s3"` if `s3_bucket` is set, else `"local"`. It SHALL return only these backend names and never any credential value.

#### Scenario: All cloud backends configured

- **WHEN** `qdrant_url`, `database_url`, and `s3_bucket` are all set
- **THEN** `active_storage()` returns `{"vectors": "qdrant", "registry": "postgres", "objects": "s3"}`

#### Scenario: Remote Chroma without Qdrant

- **WHEN** `qdrant_url` is blank but `chroma_http_url` is set
- **THEN** `active_storage()` reports vectors as `"chroma-remote"`

#### Scenario: Nothing configured falls back to local

- **WHEN** `qdrant_url`, `chroma_http_url`, `database_url`, and `s3_bucket` are all blank
- **THEN** `active_storage()` returns `{"vectors": "chroma-local", "registry": "json", "objects": "local"}`

### Requirement: Health endpoint reports config sanity without leaking secrets

The system SHALL expose `GET /api/health` returning `status`, `provider`, a `models` map for the active provider, and the `storage` backend map from `active_storage()`. For the OpenAI provider it SHALL include only the boolean `models.openai_key_set` (whether `openai_api_key` is non-empty) and SHALL NOT include the key value.

#### Scenario: Local provider health

- **WHEN** `GET /api/health` is requested with `provider == "local"`
- **THEN** the response includes `status == "ok"`, `provider == "local"`, and `models` with `transcribe` (= `whisper_model`), `embed` (= `local_embedding_model`), and `merge` (= `"ollama:" + ollama_model`)
- **AND** `storage` equals the `active_storage()` map

#### Scenario: OpenAI provider exposes only key-set boolean

- **WHEN** `GET /api/health` is requested with `provider == "openai"`
- **THEN** `models` includes `transcribe` (= `transcribe_model`), `embed` (= `embedding_model`), `merge` (= `chat_model`), and `openai_key_set` as a boolean
- **AND** the raw `openai_api_key` value never appears in the response

### Requirement: OpenAI key required with an actionable error

The system SHALL require a non-empty `openai_api_key` that is not the `sk-...` placeholder before any OpenAI client is constructed, raising a `RuntimeError` via `require_openai_key()` that instructs the operator to set `OPENAI_API_KEY` and restart.

#### Scenario: Missing or placeholder key

- **WHEN** `require_openai_key()` is called and `openai_api_key` is blank or equals `"sk-..."`
- **THEN** it raises a `RuntimeError` telling the operator to edit `.env`'s `OPENAI_API_KEY` and restart the server

#### Scenario: Valid key

- **WHEN** `require_openai_key()` is called and a real key is configured
- **THEN** it returns that key

### Requirement: Uniform API error envelope

The system SHALL shape every error response as `{"error": {"code", "message"}}`. HTTP exceptions whose detail is already a `{code, message}` dict SHALL pass through unchanged; otherwise the system SHALL map the status code to a code string (e.g. 400→`bad_request`, 401→`unauthorized`, 404→`not_found`, 409→`conflict`, 413→`payload_too_large`, 503→`service_unavailable`, unknown→`error`). Request validation failures SHALL return HTTP 422 with code `validation_error`.

#### Scenario: Known HTTP status mapped to envelope

- **WHEN** an `HTTPException` with status 404 and a plain-string detail is raised
- **THEN** the response is `{"error": {"code": "not_found", "message": <detail>}}` with status 404

#### Scenario: Pre-shaped detail passes through

- **WHEN** an `HTTPException` is raised whose detail is already a dict containing `code` and `message`
- **THEN** that dict is returned verbatim inside the `error` envelope

#### Scenario: Validation error

- **WHEN** a request fails body/form validation (`RequestValidationError`)
- **THEN** the response is HTTP 422 `{"error": {"code": "validation_error", "message": <loc: msg>}}`

### Requirement: Unhandled errors return a generic message and never leak internals

The system SHALL catch any otherwise-unhandled exception, log it server-side, and return HTTP 500 with `{"error": {"code": "internal_error", "message": "An unexpected error occurred."}}`, so stack traces, driver text, and secrets embedded in connection strings never reach the client.

#### Scenario: Unexpected server error

- **WHEN** an unhandled exception propagates out of a route handler
- **THEN** the server logs the real error (method + path) and returns HTTP 500 with the generic `internal_error` envelope
- **AND** no internal detail (stack text, DB/driver message, connection-string secrets) appears in the response body

### Requirement: Single-tenant web console gated by configuration

The system SHALL mount the server-rendered web console router only when `enable_web_console` is true (default true for local dev), and SHALL leave it unmounted (logging that it is disabled) otherwise, so production (`ENABLE_WEB_CONSOLE=false`) exposes no unauthenticated course-create / lecture-upload surface.

#### Scenario: Console enabled by default

- **WHEN** the app starts with `enable_web_console` true
- **THEN** the `web.router` is included on the app

#### Scenario: Console disabled in production

- **WHEN** the app starts with `enable_web_console` false
- **THEN** the `web.router` is NOT included and the app logs that the console is disabled

## Known deviations

- `/api/health` reads provider model fields directly (`s.whisper_model`, `s.local_embedding_model`, `s.embedding_model`, etc.) rather than calling `active_embedding_model()`; the values agree today, but the helper is not the single source for the health surface.
- `/api/health` is unauthenticated and exposes `provider`, model ids, and resolved storage backend names to any caller. It deliberately reveals only whether keys are set, never their values, but the model names and backend topology are public.
- `require_openai_key()` treats only the exact literal `"sk-..."` as a placeholder; any other malformed/dummy key passes the check and fails later inside the OpenAI SDK with its generic error.
- CORS origins are parsed from `cors_origins` at import time in `app/main.py`; changing the env var requires a process restart (uvicorn does not reload on `.env` changes), and `allow_methods`/`allow_headers` are wildcard `["*"]`.
- The blank `jwt_secret` default silently falls back to a dev-only signing key (resolved in `auth/security.py`); nothing in `config.py` or `/api/health` warns or fails if a production deployment is left with a blank `jwt_secret`.
- `Settings` does not validate `provider` against an allowed set: any unrecognized value is treated as the non-local (OpenAI) branch by `active_embedding_model()` and `/api/health`.
