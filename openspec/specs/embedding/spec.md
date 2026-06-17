# embedding

## Purpose

Provide the single embedding wrapper (`app/embed.py`) through which EVERY embedding in EchoNotes is produced — within-lecture alignment, note storage, and cross-lecture retrieval — using ONE model resolved from configuration. Centralizing embedding here keeps all vectors in the same space so cosine-similarity comparisons stay valid (Constitution Art. VI).

## Requirements

### Requirement: Single embedding entrypoint for all stages

The system SHALL produce every embedding — alignment, storage, and retrieval — through the `embed_texts` / `embed_text` functions in `app/embed.py`, and SHALL NOT embed text anywhere else, so that all vectors share one embedding space.

#### Scenario: Alignment embeds via the shared wrapper

- **WHEN** `align()` embeds slide-section text and transcript segments
- **THEN** it calls `embed_texts` from `app/embed.py`
- **AND** does not construct or call any other embedding model directly

#### Scenario: Storage and retrieval embed via the same wrapper

- **WHEN** the pipeline embeds note chunks before storing them, or `retrieve.search()` embeds a query
- **THEN** both call `embed_texts` / `embed_text` from `app/embed.py`
- **AND** therefore use the identical model and space as alignment

### Requirement: Active model resolved from configuration

The system SHALL resolve the embedding model in force from the configured `provider`: the `local_embedding_model` setting when `provider == "local"`, otherwise the `embedding_model` setting, as returned by `active_embedding_model()`.

#### Scenario: Local provider

- **WHEN** `provider` is `"local"`
- **THEN** `active_embedding_model()` returns the value of `local_embedding_model` (default `all-MiniLM-L6-v2`)

#### Scenario: OpenAI provider

- **WHEN** `provider` is `"openai"`
- **THEN** `active_embedding_model()` returns the value of `embedding_model` (default `text-embedding-3-small`)

### Requirement: Provider-specific embedding backends

The system SHALL embed text using sentence-transformers locally when `provider == "local"`, and SHALL embed text using the OpenAI embeddings endpoint otherwise, selecting the backend at call time from the current settings.

#### Scenario: Local sentence-transformers path

- **WHEN** `embed_texts` is called with a non-empty list and `provider == "local"`
- **THEN** it loads the `SentenceTransformer(local_embedding_model)` (cached via `lru_cache`)
- **AND** encodes the texts with `normalize_embeddings=True` and returns them as plain Python lists

#### Scenario: OpenAI embeddings path

- **WHEN** `embed_texts` is called with a non-empty list and `provider != "local"`
- **THEN** it calls the OpenAI client's `embeddings.create(model=embedding_model, input=texts)`
- **AND** returns the embeddings re-ordered by each result item's `index`

### Requirement: Batch and single embedding API

The system SHALL expose `embed_texts(texts)` returning one vector per input text in input order, and `embed_text(text)` returning a single vector by delegating to `embed_texts`.

#### Scenario: Single-text helper delegates to batch

- **WHEN** `embed_text(text)` is called
- **THEN** it calls `embed_texts([text])` and returns the first (only) vector

#### Scenario: Order is preserved

- **WHEN** `embed_texts` is given a list of texts
- **THEN** the returned list has one vector per input text, aligned to the input order

### Requirement: Empty input short-circuit

The system SHALL return an empty list from `embed_texts` when given an empty list, without invoking any embedding backend.

#### Scenario: Empty list

- **WHEN** `embed_texts([])` is called
- **THEN** it returns `[]`
- **AND** neither the local model nor the OpenAI client is loaded or called

### Requirement: OpenAI key required for the hosted path

The system SHALL require a configured OpenAI API key before constructing the OpenAI embeddings client, raising an actionable error (via `require_openai_key()`) when the key is unset or still the placeholder value.

#### Scenario: Missing key on the OpenAI path

- **WHEN** `embed_texts` is called with `provider == "openai"` and no valid `openai_api_key`
- **THEN** `require_openai_key()` raises a `RuntimeError` instructing the operator to set `OPENAI_API_KEY` and restart
- **AND** no embedding request is sent

### Requirement: Active embedding model surfaced in health

The system SHALL report the embedding model currently in force under the `models.embed` field of the `/api/health` response, reflecting the provider's resolved model.

#### Scenario: Health reflects the local model

- **WHEN** `GET /api/health` is requested with `provider == "local"`
- **THEN** `models.embed` equals the configured `local_embedding_model`

#### Scenario: Health reflects the OpenAI model

- **WHEN** `GET /api/health` is requested with `provider == "openai"`
- **THEN** `models.embed` equals the configured `embedding_model`

## Known deviations

- `/api/health` reads the provider's raw model setting (`s.local_embedding_model` / `s.embedding_model`) directly rather than calling the `active_embedding_model()` helper. The two are consistent today, but the helper is not the single source for the health surface.
- There is no runtime guard that all vectors in a given course were produced by the same provider/model. The single-space guarantee is enforced only by convention (one configured model at a time) and the module docstring's warning, not by stored metadata or a validation check. Switching `provider` or the model id between ingestion runs would mix incompatible vectors within a course without any error.
- `active_embedding_model()` exists as a helper but is not consumed by `embed.py`, the pipeline, alignment, or retrieval — those paths read provider/model from settings independently. Its current consumers are limited (it is not wired into the embedding call paths).
