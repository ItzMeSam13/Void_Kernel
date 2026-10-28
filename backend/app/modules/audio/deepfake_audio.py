"""
Module 4 — Audio Forensics: Deepfake Audio Entrypoint.

Re-exports synthetic audio detection functions and contracts from deepfake_detection.py
to maintain alignment with docs/architecture.md §6.
"""
from __future__ import annotations

from app.modules.audio.deepfake_detection import (
    detect_deepfake_audio,
    get_model,
    reset_model,
    run,
)
from app.modules.audio.contracts import (
    AudioDetectionInput,
    AudioDetectionOutput,
    AudioSignal,
    AudioWindowScore,
    DeepfakeAudioInput,
    DeepfakeAudioOutput,
    DetectionStatus,
)

__all__ = [
    "run",
    "detect_deepfake_audio",
    "get_model",
    "reset_model",
    "AudioDetectionInput",
    "AudioDetectionOutput",
    "DeepfakeAudioInput",
    "DeepfakeAudioOutput",
    "AudioWindowScore",
    "DetectionStatus",
    "AudioSignal",
]

