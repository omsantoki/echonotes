# transcription

## Purpose

Convert a lecture's recorded audio into an ordered list of timestamped spoken
segments (`Segment(start, end, text)` in seconds from the start of the lecture),
using either an on-machine faster-whisper model (default `provider="local"`) or
hosted OpenAI Whisper. The raw audio exists only long enough to be transcribed;
only the resulting transcript text flows downstream and is persisted (Constitution
Art. IV — never persist raw audio).

## Requirements

### Requirement: Audio is transcribed into ordered, timestamped segments

The system SHALL transcribe a lecture's audio file into a list of `Segment`
objects, each carrying `start` (seconds), `end` (seconds), and non-empty `text`,
ordered from the start of the lecture.

#### Scenario: Audio produces timestamped spoken segments

- **WHEN** `transcribe(audio_path)` is called with a readable audio file
- **THEN** the system returns a list of `Segment` instances with float `start`/`end`
  timestamps measured in seconds from the start of the lecture
- **AND** each returned segment's `text` is stripped of surrounding whitespace and
  non-empty (segments whose text is empty after stripping are omitted)

### Requirement: Transcription provider and model are configurable

The system SHALL select the transcription backend by the configured `provider`
setting, using the on-machine faster-whisper model when `provider == "local"`
(default) and hosted OpenAI Whisper otherwise, with the specific model id taken
from configuration (`whisper_model` for local, `transcribe_model` for OpenAI).

#### Scenario: Local provider uses faster-whisper

- **WHEN** `provider` is `"local"`
- **THEN** the system transcribes via faster-whisper using the `whisper_model`
  size from settings (default `"small"`)
- **AND** no OpenAI API key is required and no external ffmpeg call is made

#### Scenario: OpenAI provider uses the configured Whisper model

- **WHEN** `provider` is set to a non-local value (e.g. `"openai"`)
- **THEN** the system sends audio to the OpenAI transcriptions API using the
  `transcribe_model` from settings (default `"whisper-1"`) with
  `response_format="verbose_json"` and segment-level timestamps
- **AND** a valid OpenAI API key is required (a missing or placeholder key raises
  an actionable error before any request is made)

### Requirement: Long OpenAI audio is split and stitched

The system SHALL keep OpenAI requests under Whisper's 25 MB limit by sending files
at or below 24 MB directly, and by splitting larger files into time-based chunks
with ffmpeg, transcribing each chunk, and offsetting each chunk's segment
timestamps by its position so the returned timeline is continuous.

#### Scenario: Small file is sent directly

- **WHEN** the OpenAI provider is active and the audio file is at or below 24 MB
- **THEN** the system transcribes the file in a single request with no chunking

#### Scenario: Large file is chunked and offset

- **WHEN** the OpenAI provider is active and the audio file exceeds 24 MB
- **THEN** the system re-encodes the audio into mono 16 kHz mp3 segments of 600
  seconds each via ffmpeg, transcribes each chunk in order, and adds each chunk's
  start offset (`index * 600` seconds) to that chunk's segment timestamps
- **AND** the segments from all chunks are concatenated in chunk order

#### Scenario: Large file but ffmpeg unavailable

- **WHEN** the OpenAI provider is active, the audio exceeds 24 MB, and ffmpeg is
  not available on the system
- **THEN** the system raises a `RuntimeError` explaining the file is larger than
  the limit and instructing the caller to install ffmpeg or supply a smaller file

### Requirement: A response with only full text yields a single segment

The system SHALL still return usable transcript text when an OpenAI response
carries no per-segment timestamps, by emitting the full transcript as one segment.

#### Scenario: Response has full text but no segments

- **WHEN** an OpenAI transcription response contains no usable `segments` but has a
  non-empty `text`
- **THEN** the system returns a single `Segment` whose `text` is the full
  transcript and whose `start` and `end` both equal the current chunk offset

### Requirement: Raw audio is never persisted

The system SHALL treat the audio file as transient: the transcription path opens
or reads the file only to produce the transcript and never copies, uploads, or
writes the raw audio to durable storage. The caller deletes the audio immediately
after transcription returns and removes the entire upload workspace even on failure.

#### Scenario: Audio deleted right after transcription

- **WHEN** transcription of a lecture's audio completes in the pipeline
- **THEN** the audio file is deleted before any further processing step runs
- **AND** the upload workspace is removed in a `finally` block so no recording
  survives even if a later step fails

#### Scenario: Only transcript text leaves the transcription step

- **WHEN** `transcribe` returns
- **THEN** the only data produced is the list of `Segment` text/timestamps, and the
  audio bytes are not retained or returned by the function
