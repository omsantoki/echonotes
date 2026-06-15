"""Transcription (task T011): audio -> timestamped segments.

OpenAI Whisper (`whisper-1`) returns verbose JSON with per-segment timestamps.
Lectures routinely exceed the API's 25 MB limit, so long audio is split into
time-based chunks with ffmpeg and the segment timestamps are stitched back
together. Raw audio is NEVER persisted — the caller deletes the temp file the
moment this returns (Constitution Art. IV).
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from openai import OpenAI

from app.config import get_settings, require_openai_key

# Whisper's hard limit is 25 MB; stay under it with margin.
_MAX_DIRECT_BYTES = 24 * 1024 * 1024
_CHUNK_SECONDS = 600  # 10-minute chunks when splitting long audio


@dataclass
class Segment:
    """One spoken span, in seconds from the start of the lecture."""

    start: float
    end: float
    text: str


@lru_cache
def _client() -> OpenAI:
    return OpenAI(api_key=require_openai_key())


def transcribe(audio_path: str | Path) -> list[Segment]:
    """Transcribe a lecture's audio into ordered, timestamped segments."""
    audio_path = Path(audio_path)
    if get_settings().provider == "local":
        return _transcribe_local(audio_path)
    # OpenAI Whisper: split past the 25 MB limit, otherwise send directly.
    if audio_path.stat().st_size <= _MAX_DIRECT_BYTES:
        return _transcribe_one(audio_path, offset=0.0)
    return _transcribe_chunked(audio_path)


def _transcribe_local(path: Path) -> list[Segment]:
    """faster-whisper, on this machine. Handles long audio natively (no 25 MB
    limit, no external ffmpeg — audio is decoded via the bundled av library)."""
    model = _faster_whisper()
    segments, _info = model.transcribe(str(path))
    out: list[Segment] = []
    for s in segments:  # generator — consuming it runs the transcription
        text = (s.text or "").strip()
        if text:
            out.append(Segment(start=float(s.start), end=float(s.end), text=text))
    return out


@lru_cache
def _faster_whisper():
    from faster_whisper import WhisperModel
    # int8 keeps it fast on CPU; weights download + cache on first use.
    return WhisperModel(get_settings().whisper_model, device="auto", compute_type="int8")


def _transcribe_one(path: Path, offset: float) -> list[Segment]:
    model = get_settings().transcribe_model
    with path.open("rb") as fh:
        resp = _client().audio.transcriptions.create(
            model=model,
            file=fh,
            response_format="verbose_json",
            timestamp_granularities=["segment"],
        )
    out: list[Segment] = []
    for s in getattr(resp, "segments", None) or []:
        text = str(_get(s, "text", "")).strip()
        if text:
            out.append(Segment(
                start=float(_get(s, "start", 0.0)) + offset,
                end=float(_get(s, "end", 0.0)) + offset,
                text=text,
            ))
    if not out:
        # Some responses carry only the full text — keep it as one segment.
        text = str(getattr(resp, "text", "")).strip()
        if text:
            out.append(Segment(start=offset, end=offset, text=text))
    return out


def _transcribe_chunked(path: Path) -> list[Segment]:
    if not _have_ffmpeg():
        mb = _MAX_DIRECT_BYTES // (1024 * 1024)
        raise RuntimeError(
            f"Audio is larger than {mb} MB and ffmpeg is unavailable to split it. "
            "Install ffmpeg or supply a smaller / compressed file."
        )
    out: list[Segment] = []
    with tempfile.TemporaryDirectory() as tmp:
        pattern = os.path.join(tmp, "chunk_%04d.mp3")
        # Re-encode to mono 16 kHz mp3 segments: small, uniform, Whisper-friendly.
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(path), "-ac", "1", "-ar", "16000",
             "-f", "segment", "-segment_time", str(_CHUNK_SECONDS), pattern],
            check=True, capture_output=True,
        )
        for i, chunk in enumerate(sorted(Path(tmp).glob("chunk_*.mp3"))):
            out.extend(_transcribe_one(chunk, offset=float(i * _CHUNK_SECONDS)))
    return out


def _have_ffmpeg() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], check=True, capture_output=True)
        return True
    except (OSError, subprocess.CalledProcessError):
        return False


def _get(obj, key, default):
    return obj.get(key, default) if isinstance(obj, dict) else getattr(obj, key, default)
