# diagram-description

## Purpose

Produce a short, student-facing description of a meaningful (non-decorative) slide diagram image using a vision-capable LLM, so the diagram can be explained in the notes and indexed for search. It is a Strong-tier, best-effort capability: when no vision model is available or the call fails, it returns `None` and the surrounding pipeline keeps the diagram with its plain caption, leaving Core behavior unchanged.

## Requirements

### Requirement: Describe meaningful diagram images via a vision model

The system SHALL accept raw image bytes, an image extension, and a topic string, and return a concise (1-3 sentence) description of the diagram produced by a vision-capable chat model, or `None` when no usable description is produced.

#### Scenario: A meaningful diagram is described

- **WHEN** `describe_image` is called with non-empty image bytes for an instructional diagram and diagram description is enabled
- **THEN** the system sends the image plus a topic-aware prompt to the vision model
- **AND** returns the model's stripped text description (not `None`)

### Requirement: Respect the describe-diagrams setting

The system SHALL only attempt a vision-model call when the `describe_diagrams` setting is enabled.

#### Scenario: Description disabled by configuration

- **WHEN** `describe_image` is called while the `describe_diagrams` setting is `False`
- **THEN** the system returns `None` without making any vision-model call

### Requirement: Skip empty input

The system SHALL return `None` without calling the vision model when the supplied image bytes are empty or falsy.

#### Scenario: No image bytes provided

- **WHEN** `describe_image` is called with empty image bytes
- **THEN** the system returns `None` and makes no vision-model call

### Requirement: Treat decorative or empty replies as no description

The system SHALL return `None` when the model's reply is empty or begins (case-insensitively) with `SKIP`, so decorative content (logos, photos, content with no instructional value) yields no description.

#### Scenario: Model flags the image as decorative

- **WHEN** the vision model replies with text whose uppercase form starts with `SKIP`
- **THEN** the system returns `None` instead of returning that reply

#### Scenario: Model returns an empty reply

- **WHEN** the vision model returns empty or whitespace-only content
- **THEN** the system returns `None`

### Requirement: Best-effort failure handling

The system SHALL catch any exception raised while building the client, selecting the model, or calling the vision model, and return `None` rather than propagating the error, so a missing or failing vision model never aborts the surrounding pipeline.

#### Scenario: Vision-model call raises an error

- **WHEN** the vision-model API call or client construction raises any exception (for example, no model available, network failure, or a missing OpenAI key)
- **THEN** the system swallows the exception and returns `None`
- **AND** the calling pipeline keeps the diagram with no description attached

### Requirement: Provider-aware model and client selection

The system SHALL choose its vision client and model from the active provider: a local Ollama vision model when the provider is `local`, otherwise the OpenAI multimodal chat model (requiring a configured OpenAI key).

#### Scenario: Local provider

- **WHEN** the active provider is `local`
- **THEN** the system targets the Ollama OpenAI-compatible endpoint and uses the configured Ollama vision model

#### Scenario: OpenAI provider

- **WHEN** the active provider is not `local`
- **THEN** the system constructs an OpenAI client using the required OpenAI key and uses the configured chat model

### Requirement: Topic-aware, concept-only prompting

The system SHALL prompt the model with the diagram's topic and instruct it to describe the concept in 1-3 sentences, to avoid inventing values, and to reply with exactly `SKIP` for decorative images.

#### Scenario: Prompt is built from the topic

- **WHEN** `describe_image` issues a vision request
- **THEN** the prompt text includes the supplied topic and the instructions to capture the concept (not every label), to never invent values, and to reply `SKIP` for decorative images
- **AND** the image is sent as a base64 data URL whose media type uses the provided extension (defaulting to `png`)

## Known deviations

- The exception handler is a blanket `except Exception` that returns `None`, so all failure modes (no vision model, network error, malformed response, or a missing OpenAI key surfaced by `require_openai_key`) are collapsed into a silent `None` with no logging or distinction between them.
- The OpenAI client is memoized with `lru_cache` on `_client()` with no arguments, so the client is constructed once per process. Changing the provider or relevant settings at runtime would not rebuild the client until the process restarts.
- The `SKIP` sentinel is matched with `text.upper().startswith("SKIP")`, so any model reply that merely begins with the letters "SKIP" (for example, a sentence starting with "Skipping ...") is treated as decorative and discarded, even if it contains a real description.
- The capability deliberately conveys the diagram's concept rather than extracting every value or label, honoring the constitution's "no deep diagram parsing" boundary; it is not a faithful data-extraction tool.
