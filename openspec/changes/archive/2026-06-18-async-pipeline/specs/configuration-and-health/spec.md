## ADDED Requirements

### Requirement: Async task and cache mode surfaced without credentials

The system SHALL resolve how asynchronous work and the semantic cache are configured via `active_async()`, based solely on whether `redis_url` is set and the `task_always_eager` flag: `tasks` reports `"celery"` when `redis_url` is set and `task_always_eager` is false, else `"inline"`; `broker` reports `"redis"` when `redis_url` is set, else `"none"`; `cache` reports `"redis"` when `redis_url` is set, else `"off"`. It SHALL return only these names and never any connection string or credential.

#### Scenario: Redis configured with workers

- **WHEN** `redis_url` is set and `task_always_eager` is false
- **THEN** `active_async()` returns `{"tasks": "celery", "broker": "redis", "cache": "redis"}`

#### Scenario: Local dev defaults

- **WHEN** `redis_url` is blank
- **THEN** `active_async()` returns `{"tasks": "inline", "broker": "none", "cache": "off"}`
- **AND** no connection string appears in the result

## MODIFIED Requirements

### Requirement: Health endpoint reports config sanity without leaking secrets

The system SHALL expose `GET /api/health` returning `status`, `provider`, a `models` map for the active provider, the `storage` backend map from `active_storage()`, and the `async` map from `active_async()`. For the OpenAI provider it SHALL include only the boolean `models.openai_key_set` (whether `openai_api_key` is non-empty) and SHALL NOT include the key value.

#### Scenario: Local provider health

- **WHEN** `GET /api/health` is requested with `provider == "local"`
- **THEN** the response includes `status == "ok"`, `provider == "local"`, and `models` with `transcribe` (= `whisper_model`), `embed` (= `local_embedding_model`), and `merge` (= `"ollama:" + ollama_model`)
- **AND** `storage` equals the `active_storage()` map
- **AND** `async` equals the `active_async()` map

#### Scenario: OpenAI provider exposes only key-set boolean

- **WHEN** `GET /api/health` is requested with `provider == "openai"`
- **THEN** `models` includes `transcribe` (= `transcribe_model`), `embed` (= `embedding_model`), `merge` (= `chat_model`), and `openai_key_set` as a boolean
- **AND** the raw `openai_api_key` value never appears in the response

#### Scenario: Async mode reported

- **WHEN** `GET /api/health` is requested
- **THEN** the response includes an `async` object with `tasks`, `broker`, and `cache` fields and no credential values
