# note-merge

## Purpose

Note-merge synthesizes, per slide section, the union of the written slide text and the aligned spoken transcript into one clean, de-duplicated set of study-note blocks. Every block carries a `source_type` (`slides` or `spoken`) and an explainable `reason`; points that came only from speech are flagged so the UI can emphasize them. An optional second LLM refine pass rewrites and de-duplicates a section's blocks into a single narrative without dropping the provenance labels.

## Requirements

### Requirement: Merge a section's slide and spoken content into labeled blocks

The system SHALL compose the note blocks for one slide section by sending that section's stripped slide text and its space-joined aligned spoken text to an LLM that returns an ordered list of segments, each parsed into a `Block` carrying `source_type`, `text`, `reason`, `confidence`, and `spoken_only`.

#### Scenario: Section with slide text and aligned speech

- **WHEN** `merge_section` is called with a `SectionAlignment` whose section has slide text and whose `spoken` list is non-empty
- **THEN** the system computes the spoken text as the spoken segments' texts joined by a single space and stripped, and the spoken confidence as the mean of the aligned segments' scores
- **AND** it sends a JSON user message containing the section title as `topic`, the slide text as `SLIDES`, and the spoken text as `TRANSCRIPT` to the chat model with the union/deduplicate/reconstruct system prompt
- **AND** it returns the parsed list of `Block` segments produced from the model's JSON response

#### Scenario: Section with no slide text and no speech

- **WHEN** `merge_section` is called with a section whose stripped slide text is empty and whose joined spoken text is empty
- **THEN** the system returns an empty list of blocks and does not call the LLM

### Requirement: Every block carries a source label and an explainable reason

The system SHALL accept a parsed segment only when its `source_type` is exactly `slides` or `spoken` and its stripped text is non-empty, and SHALL assign every accepted block a non-empty `reason`, substituting a default reason when the model supplies none.

#### Scenario: Valid segment retained with model reason

- **WHEN** a model segment has `source_type` of `slides` or `spoken` and non-empty text
- **THEN** a `Block` is created with that source type and stripped text
- **AND** its reason is the model's stripped reason when present

#### Scenario: Missing reason gets a default

- **WHEN** an accepted segment has no reason (or only whitespace)
- **THEN** the block's reason defaults to "From the slides." for a `slides` segment and "Said in the lecture." for a `spoken` segment

#### Scenario: Invalid segment dropped

- **WHEN** a model segment has a `source_type` other than `slides`/`spoken`, or has empty text
- **THEN** that segment is skipped and produces no block

### Requirement: Confidence derived from source

The system SHALL set a merged block's confidence to 1.0 when its source type is `slides`, and to the section's spoken confidence rounded to three decimals when its source type is `spoken`.

#### Scenario: Slide block confidence

- **WHEN** an accepted block has source type `slides`
- **THEN** its confidence is 1.0

#### Scenario: Spoken block confidence

- **WHEN** an accepted block has source type `spoken`
- **THEN** its confidence is the mean alignment score of the section's spoken segments, rounded to three decimals

### Requirement: Emphasize spoken-only content

The system SHALL flag a block as `spoken_only` only when the model marks the segment as spoken-only AND the block's source type is `spoken`, so that content not present on the slides is distinguished for emphasis.

#### Scenario: Spoken-only flag honored for spoken segment

- **WHEN** a model segment is marked spoken-only and has source type `spoken`
- **THEN** the resulting block's `spoken_only` is true

#### Scenario: Spoken-only flag ignored for slide segment

- **WHEN** a model segment is marked spoken-only but has source type `slides`
- **THEN** the resulting block's `spoken_only` is false

### Requirement: Never lose content when the LLM fails

The system SHALL fall back to deterministic blocks whenever the merge LLM call, JSON decoding, or parsing raises an exception, or when parsing yields no usable segments, so that source content is preserved.

#### Scenario: LLM call or parsing fails

- **WHEN** the merge model call, JSON parse, or segment parse raises an exception
- **THEN** the system swallows the exception and returns fallback blocks
- **AND** a non-empty slide text produces one `slides` block (confidence 1.0) and a non-empty spoken text produces one `spoken` block flagged `spoken_only` with the rounded spoken confidence

#### Scenario: Model returns no usable segments

- **WHEN** the model responds but parsing produces an empty block list
- **THEN** the system returns the same fallback blocks rather than an empty result

### Requirement: Optional refine pass preserves provenance

The system SHALL run a second LLM refine pass over a topic's merged blocks only when the `refine_notes` setting is enabled and the block list is non-empty, rewriting and de-duplicating the prose while keeping every refined block labeled with `source_type` and `spoken_only`; otherwise it SHALL return the merged blocks unchanged.

#### Scenario: Refine disabled or no blocks

- **WHEN** `refine_section` is called while `refine_notes` is false, or with an empty block list
- **THEN** the input blocks are returned unchanged and no LLM call is made

#### Scenario: Refine produces a de-duplicated narrative

- **WHEN** `refine_notes` is enabled and `refine_section` receives non-empty blocks
- **THEN** the system sends the topic plus each block's `source_type`, `text`, and `spoken_only` to the refine model with the preserve-everything system prompt
- **AND** it returns refined blocks each carrying a `source_type`, non-empty text (defaulting the reason to "Refined, de-duplicated study note." when absent), a confidence of 1.0 for `slides` or the original spoken confidence (defaulting to 0.8) for `spoken`, and `spoken_only` only when the model marks it and the source is `spoken`

#### Scenario: Refine failure falls back to the merge

- **WHEN** the refine model call or parsing raises an exception, or yields no usable segments
- **THEN** the system returns the original merged blocks unchanged

## Known deviations

- Reasons are not enforced to be substantive: the parser only requires a non-empty `source_type` and text. If the model omits the reason it is replaced by a generic default ("From the slides.", "Said in the lecture.", or "Refined, de-duplicated study note."), so a block can carry a boilerplate rather than a truly explanatory reason.
- The spoken-only star emphasis ("★ Spoken-only (not on the slides) — …") is not applied by `merge.py`/`refine.py`; it is added downstream in `pipeline._compose_chunks` when building `NoteChunk`s. The merge/refine layer only sets the boolean `spoken_only` flag.
- The refine pass reads the original blocks' spoken confidence from the first `spoken` block only and applies that single value to all refined spoken blocks; it does not recompute per-segment confidence, and falls back to a hard-coded 0.8 when no spoken block exists.
- `_fallback_segments` collapses all spoken content into one block (and all slide text into one block) with fixed reasons, losing the per-segment structure and any model-derived spoken-only distinctions; the entire spoken fallback block is always flagged `spoken_only` even though some of that speech may restate the slides.
- Both `merge_section` and `refine_section` catch all exceptions broadly with a bare `except Exception: pass`, so provider/model errors are silently swallowed with no logging.
- The model selection and client are provider-dependent and memoized via `lru_cache`: for `provider="local"` an OpenAI-compatible Ollama client/model is used; otherwise the OpenAI client with `chat_model` (merge) or `refine_model` (refine, when set) is used. There is no validation that the configured model actually returns the requested JSON shape beyond the parse-and-skip logic.
