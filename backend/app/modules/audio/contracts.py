"""
modules/audio/contracts.py — Module 4 public contracts (Person 3 owns this).

AudioInput / AudioFindings form the ONLY interface surface of Module 4.
"""
from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field


AudioSignal = Literal[
    "synthetic_audio_signal_detected",
    "no_strong_signal_detected",
    "inconclusive",
    "not_assessed",
]


class AudioInput(BaseModel):
    """Input to Module 4's run() entrypoint."""
    audio_path:  Optional[str]  = Field(None, description="Local path to the audio/video file.")
    audio_bytes: Optional[bytes] = Field(None, description="Raw audio bytes (alternative to path).")


class AudioFindings(BaseModel):
    """
    Output of Module 4's run() entrypoint.
    Matches the stub in orchestrator/state.py — keep in sync.
    """
    transcript:               Optional[str]         = Field(None,
        description="Whisper transcription of spoken audio.")
    synthetic_audio_signal:   Optional[AudioSignal] = Field(None,
        description="Wav2Vec2 deepfake-audio verdict.")
    synthetic_audio_confidence: Optional[float]     = Field(None, ge=0.0, le=1.0)
    av_sync_ok:               Optional[bool]        = Field(None,
        description="SyncNet A/V sync check (optional, None if not run).")
    error:                    Optional[str]          = None
