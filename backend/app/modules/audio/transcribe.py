"""
Module 4 — Audio Forensics: Transcribe Entrypoint.

Re-exports speech transcription functions and contracts from transcription.py
to maintain alignment with docs/architecture.md §6.
"""
from __future__ import annotations

from app.modules.audio.transcription import (
    get_model,
    reset_model,
    run,
    transcribe_audio,
)
from app.modules.audio.contracts import (
    AudioTranscriptionInput,
    AudioTranscriptionOutput,
    TranscriptSegment,
    TranscriptionStatus,
)

__all__ = [
    "run",
    "transcribe_audio",
    "get_model",
    "reset_model",
    "AudioTranscriptionInput",
    "AudioTranscriptionOutput",
    "TranscriptSegment",
    "TranscriptionStatus",
]

