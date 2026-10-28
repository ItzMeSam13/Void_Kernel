"""
Module 4 — Audio Forensics (Person 3).

Sub-components:
- Speech transcription via faster-whisper (transcription.py / transcribe.py)
- Synthetic-audio detector via Wav2Vec2 (deepfake_detection.py / deepfake_audio.py)
- Optional: SyncNet A/V sync (av_sync.py — Phase 4 stretch)

Public entrypoints:
- transcribe_audio(audio_path, language=None, model_size=None) -> AudioTranscriptionOutput
- run_transcription(input: AudioTranscriptionInput) -> AudioTranscriptionOutput
- detect_deepfake_audio(audio_path, ...) -> AudioDetectionOutput
- run_detection(input: AudioDetectionInput) -> AudioDetectionOutput
- run(inp: AudioInput) -> AudioFindings (Module 4 top-level orchestrator entrypoint)
"""
from __future__ import annotations

from typing import Union

from app.modules.audio.contracts import (
    AudioDetectionInput,
    AudioDetectionOutput,
    AudioFindings,
    AudioInput,
    AudioSignal,
    AudioTranscriptionInput,
    AudioTranscriptionOutput,
    AudioWindowScore,
    DeepfakeAudioInput,
    DeepfakeAudioOutput,
    DetectionStatus,
    TranscriptSegment,
    TranscriptionInput,
    TranscriptionOutput,
    TranscriptionStatus,
)
from app.modules.audio.deepfake_detection import (
    detect_deepfake_audio,
    get_model as get_detection_model,
    reset_model as reset_detection_model,
    run as run_detection,
)
from app.modules.audio.transcription import (
    get_model as get_transcription_model,
    reset_model as reset_transcription_model,
    run as run_transcription,
    transcribe_audio,
)


async def run(
    inp: Union[AudioInput, AudioTranscriptionInput, AudioDetectionInput]
) -> Union[AudioFindings, AudioTranscriptionOutput, AudioDetectionOutput]:
    """
    Module 4 public entrypoint.

    Handles:
    - AudioTranscriptionInput -> returns AudioTranscriptionOutput directly.
    - AudioDetectionInput -> returns AudioDetectionOutput directly.
    - AudioInput -> executes both speech transcription and synthetic-audio detection,
      returning aggregated AudioFindings.
    """
    if isinstance(inp, AudioTranscriptionInput):
        return run_transcription(inp)

    if isinstance(inp, AudioDetectionInput):
        return run_detection(inp)

    # AudioInput path (orchestrator / pipeline)
    if not inp.audio_path:
        return AudioFindings(error="No audio_path provided to audio module.")

    # 1. Run transcription
    tx_res = run_transcription(AudioTranscriptionInput(audio_path=inp.audio_path))
    
    # 2. Run synthetic audio detection
    det_res = run_detection(AudioDetectionInput(audio_path=inp.audio_path))

    errors: list[str] = []
    if tx_res.status == TranscriptionStatus.ERROR and tx_res.error_message:
        errors.append(f"Transcription error: {tx_res.error_message}")
    if det_res.status == DetectionStatus.ERROR and det_res.error_message:
        errors.append(f"Detection error: {det_res.error_message}")

    combined_error = "; ".join(errors) if errors else None

    return AudioFindings(
        transcript=tx_res.transcript if tx_res.status != TranscriptionStatus.ERROR else None,
        transcription_details=tx_res,
        synthetic_audio_signal=det_res.verdict,
        synthetic_audio_confidence=det_res.synthetic_audio_confidence,
        detection_details=det_res,
        av_sync_ok=None,
        error=combined_error,
    )


__all__ = [
    "run",
    "run_transcription",
    "transcribe_audio",
    "run_detection",
    "detect_deepfake_audio",
    "get_transcription_model",
    "reset_transcription_model",
    "get_detection_model",
    "reset_detection_model",
    "AudioInput",
    "AudioFindings",
    "AudioSignal",
    "AudioTranscriptionInput",
    "AudioTranscriptionOutput",
    "TranscriptionInput",
    "TranscriptionOutput",
    "TranscriptSegment",
    "TranscriptionStatus",
    "AudioDetectionInput",
    "AudioDetectionOutput",
    "DeepfakeAudioInput",
    "DeepfakeAudioOutput",
    "AudioWindowScore",
    "DetectionStatus",
]
