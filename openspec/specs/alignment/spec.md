# alignment

## Purpose

Alignment matches each spoken transcript segment to the slide section(s) it best corresponds to, using cosine similarity over the one configured embedding model. Grouping spoken content under slide sections is the foundation for source labeling and topic-organized merging downstream.

## Requirements

### Requirement: Single embedding model for both sides

The system SHALL embed slide-section text and transcript-segment text using the one configured embedding model via `embed_texts`, and SHALL NOT use any other embedding source for alignment.

#### Scenario: Sections and segments embedded with the same model

- **WHEN** `align` is called with non-empty slide sections and spoken segments
- **THEN** the system builds one section text per section as the section title and text joined by a newline and stripped
- **AND** it embeds the section texts and the segment texts by calling `embed_texts`, the single shared embedding entry point

### Requirement: Cosine similarity scoring

The system SHALL compute the match between a spoken segment and a slide section as cosine similarity, by unit-normalizing every embedding vector and taking the dot product of segment vectors against section vectors.

#### Scenario: Similarity matrix computed from normalized vectors

- **WHEN** alignment runs over the embedded section and segment vectors
- **THEN** each embedding vector is divided by its L2 norm before scoring
- **AND** a zero-norm vector is treated as having norm 1.0 so it is left unchanged rather than producing a divide-by-zero
- **AND** the per-pair score is the dot product of the normalized segment and section vectors

### Requirement: Best slide section always retained

The system SHALL attach every spoken segment to its single best-matching slide section, regardless of how low that segment's best similarity is.

#### Scenario: Segment grouped under its top section

- **WHEN** a spoken segment is scored against all slide sections
- **THEN** the section with the highest cosine similarity is selected as the best match
- **AND** the segment is added to that section's spoken list even when no other section qualifies

### Requirement: Near-tie runner-up sections

The system SHALL also attach a spoken segment to additional runner-up slide sections, but only up to the configured top-k count and only while a runner-up's clipped score is at least 0.85 times the best-match clipped score.

#### Scenario: Close runner-up is attached

- **WHEN** a runner-up section among the top-k ranked sections has a score at least 0.85 of the best score
- **THEN** the segment is also added to that runner-up section's spoken list

#### Scenario: Distant runner-up stops further attachment

- **WHEN** a runner-up section's score falls below 0.85 of the best score
- **THEN** attachment for that segment stops at that rank and no further (lower-ranked) sections receive the segment

#### Scenario: Top-k bound respected

- **WHEN** the configured `align_top_k` (default 3) is reached
- **THEN** no more than that many sections receive a single segment, and the effective k is never less than 1

### Requirement: Confidence and reason on every match

The system SHALL record on each attached spoken segment an alignment confidence score clipped to the range [0, 1] and a human-readable reason describing the matched section title, the score, and the segment's rank among the slide sections.

#### Scenario: Aligned segment carries explainable metadata

- **WHEN** a spoken segment is attached to a slide section
- **THEN** an `AlignedSegment` is created carrying the original segment text, start, and end times
- **AND** its score is the cosine similarity clipped into [0, 1]
- **AND** its reason states the matched section title, the score to two decimals, and the rank as "top-N of M slide sections"

### Requirement: Empty-input handling

The system SHALL return one `SectionAlignment` per slide section with an empty spoken list when there are no slide sections or no spoken segments, performing no embedding in that case.

#### Scenario: No segments to align

- **WHEN** `align` is called with slide sections but an empty segment list
- **THEN** it returns a `SectionAlignment` for each section with no spoken segments attached and does not call the embedding model

#### Scenario: No slide sections

- **WHEN** `align` is called with an empty slide-section list
- **THEN** it returns an empty result list and does not call the embedding model
