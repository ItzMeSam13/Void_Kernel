"""
modules/audio/__init__.py — Module 4 public entrypoint (stub).

Person 3 implements Whisper transcription + Wav2Vec2 deepfake-audio here.
"""
from __future__ import annotations

from app.modules.audio.contracts import AudioInput, AudioFindings


async def run(inp: AudioInput) -> AudioFindings:
    """
    STUB — Person 3 replaces this body.

    Full implementation:
      1. FFmpeg audio extraction → mono 16kHz WAV.
      2. Whisper small transcription → claim text handed to Module 6.
      3. Wav2Vec2 deepfake-audio scorer (mo-thecreator/Deepfake-audio-detection).
      4. (Optional) SyncNet A/V sync cross-check.
    """
    return AudioFindings(
        error="Module 4 (audio) not yet implemented — stub."
    )
