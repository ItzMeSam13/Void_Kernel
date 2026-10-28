"""
modules/audio/contracts.py — Module 4 public contracts (Person 3 owns this).

Defines typed input/output contracts for:
1. Speech transcription via faster-whisper (AudioTranscriptionInput / AudioTranscriptionOutput).
2. Synthetic audio / deepfake detection via Wav2Vec2 (AudioDetectionInput / AudioDetectionOutput).
3. Module 4's top-level findings (AudioInput / AudioFindings).

Architecture rule (§6): this file contains Pydantic models only.
Zero dependencies on FastAPI, LangGraph, or other modules.
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field, model_validator


# ── Speech Transcription Contracts ──────────────────────────────────────────

class TranscriptionStatus(str, Enum):
    """Outcome of an audio speech transcription run."""
    SUCCESS = "success"
    NO_SPEECH_DETECTED = "no_speech_detected"
    ERROR = "error"


class TranscriptSegment(BaseModel):
    """A single timestamped segment of recognized speech."""
    start: float = Field(..., ge=0.0, description="Start timestamp in seconds.")
    end: float = Field(..., ge=0.0, description="End timestamp in seconds.")
    text: str = Field(..., description="Recognized speech text for this segment.")
    no_speech_prob: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Probability that this segment contains no speech.",
    )

    @model_validator(mode="after")
    def validate_timestamps(self) -> TranscriptSegment:
        if self.end < self.start:
            raise ValueError(
                f"Segment end timestamp ({self.end}s) cannot be before start timestamp ({self.start}s)"
            )
        return self


class AudioTranscriptionInput(BaseModel):
    """Input contract for the speech transcription component."""
    audio_path: str = Field(
        ...,
        min_length=1,
        description="Local path to the extracted audio file (.wav, .mp3, etc.).",
    )
    language: Optional[str] = Field(
        None,
        description=(
            "Optional spoken language code hint (e.g. 'en', 'es', 'fr'). "
            "If None, Whisper will automatically detect the language."
        ),
    )
    model_size: Optional[str] = Field(
        None,
        description=(
            "Optional override for the Whisper model size (e.g. 'small', 'tiny'). "
            "Defaults to configured WHISPER_MODEL_SIZE or 'small'."
        ),
    )


class AudioTranscriptionOutput(BaseModel):
    """
    Output contract for the speech transcription component.
    
    Contains the full assembled transcript, timestamped segments,
    detected language metadata, and processing status.
    """
    status: TranscriptionStatus = Field(
        ...,
        description="Outcome of transcription: success, no_speech_detected, or error.",
    )
    transcript: str = Field(
        default="",
        description="Full assembled transcript text from all segments.",
    )
    segments: List[TranscriptSegment] = Field(
        default_factory=list,
        description="Chronologically ordered timestamped transcript segments.",
    )
    language: Optional[str] = Field(
        None,
        description="Detected or specified spoken language code (e.g. 'en').",
    )
    language_probability: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description=(
            "Model confidence in detected language. "
            "NOTE: This is NOT transcription accuracy or factual truth."
        ),
    )
    duration: Optional[float] = Field(
        None,
        ge=0.0,
        description="Duration of the audio file in seconds, if available.",
    )
    model_size: str = Field(
        default="small",
        description="Whisper model size or identifier used for inference.",
    )
    error_message: Optional[str] = Field(
        None,
        description="Human-readable error description when status is 'error'.",
    )


# Convenience aliases matching repo conventions
TranscriptionInput = AudioTranscriptionInput
TranscriptionOutput = AudioTranscriptionOutput


# ── Synthetic Audio / Deepfake Detection Contracts (Wav2Vec2) ───────────────

class DetectionStatus(str, Enum):
    """Processing outcome of a synthetic-audio detection run."""
    SUCCESS = "success"
    SILENCE_OR_EMPTY = "silence_or_empty"
    NOT_ASSESSED = "not_assessed"
    ERROR = "error"


AudioSignal = Literal[
    "synthetic_audio_signal_detected",
    "no_strong_signal_detected",
    "inconclusive",
    "not_assessed",
]


class AudioWindowScore(BaseModel):
    """Detection scores for a single temporal analysis window."""
    start_sec: float = Field(..., ge=0.0, description="Window start time in seconds.")
    end_sec: float = Field(..., ge=0.0, description="Window end time in seconds.")
    fake_score: float = Field(..., ge=0.0, le=1.0, description="Model probability of 'fake' (synthetic).")
    real_score: float = Field(..., ge=0.0, le=1.0, description="Model probability of 'real' (bonafide).")
    predicted_label: str = Field(..., description="Predicted class label for this window ('fake' or 'real').")

    @model_validator(mode="after")
    def validate_timestamps(self) -> AudioWindowScore:
        if self.end_sec < self.start_sec:
            raise ValueError(
                f"Window end ({self.end_sec}s) cannot be earlier than start ({self.start_sec}s)"
            )
        return self


class AudioDetectionInput(BaseModel):
    """Input contract for the Wav2Vec2 synthetic audio detection component."""
    audio_path: str = Field(
        ...,
        min_length=1,
        description="Local path to audio file (.wav, .mp3, etc.).",
    )
    threshold: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Threshold on fake_score for classifying as synthetic_audio_signal_detected.",
    )
    window_duration_sec: Optional[float] = Field(
        None,
        gt=0.0,
        description="Duration of each analysis window in seconds for chunked inference on long audio.",
    )
    window_overlap_sec: Optional[float] = Field(
        None,
        ge=0.0,
        description="Overlap between consecutive analysis windows in seconds.",
    )
    model_id: Optional[str] = Field(
        None,
        description="Optional Hugging Face model identifier override.",
    )


class AudioDetectionOutput(BaseModel):
    """
    Output contract for the Wav2Vec2 synthetic audio detection component.

    Provides raw class probabilities, predicted label, qualified verdict signal,
    audio duration, and optional per-window analysis for long audio.
    """
    status: DetectionStatus = Field(
        ...,
        description="Processing status: success, silence_or_empty, not_assessed, or error.",
    )
    verdict: AudioSignal = Field(
        default="not_assessed",
        description="Qualified authenticity signal: synthetic_audio_signal_detected, no_strong_signal_detected, inconclusive, or not_assessed.",
    )
    synthetic_audio_confidence: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Confidence associated with the verdict signal.",
    )
    fake_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Aggregate model probability that the audio is synthetic/manipulated.",
    )
    real_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Aggregate model probability that the audio is authentic/bonafide.",
    )
    class_probabilities: Dict[str, float] = Field(
        default_factory=dict,
        description="Mapping of class name to probability (e.g. {'fake': 0.85, 'real': 0.15}).",
    )
    predicted_label: Optional[str] = Field(
        None,
        description="Raw predicted class label from the classifier ('fake' or 'real').",
    )
    audio_duration: Optional[float] = Field(
        None,
        ge=0.0,
        description="Total duration of the audio in seconds.",
    )
    model_id: str = Field(
        default="mo-thecreator/Deepfake-audio-detection",
        description="Hugging Face model checkpoint used for classification.",
    )
    window_scores: List[AudioWindowScore] = Field(
        default_factory=list,
        description="Per-window breakdown for recordings processed in temporal chunks.",
    )
    error_message: Optional[str] = Field(
        None,
        description="Human-readable error description when status is 'error'.",
    )
    limitations: Optional[str] = Field(
        default=(
            "Wav2Vec2 detection score is an authenticity signal, not definitive proof of manipulation. "
            "Model generalization to unseen audio codecs, noise, or novel speech synthesis algorithms "
            "is not guaranteed."
        ),
        description="Documented forensic limitations of the detector.",
    )


# Convenience aliases
DeepfakeAudioInput = AudioDetectionInput
DeepfakeAudioOutput = AudioDetectionOutput


# ── Top-level Module 4 Contracts ────────────────────────────────────────────

class AudioInput(BaseModel):
    """Input to Module 4's top-level run() entrypoint."""
    audio_path: Optional[str] = Field(None, description="Local path to the audio file.")
    audio_bytes: Optional[bytes] = Field(None, description="Raw audio bytes (alternative to path).")


class AudioFindings(BaseModel):
    """
    Output of Module 4's top-level run() entrypoint.
    Matches the schema in orchestrator/state.py — keep in sync.
    """
    transcript: Optional[str] = Field(
        None,
        description="Whisper transcription of spoken audio.",
    )
    transcription_details: Optional[AudioTranscriptionOutput] = Field(
        None,
        description="Detailed transcription result including segments and timestamps.",
    )
    synthetic_audio_signal: Optional[AudioSignal] = Field(
        None,
        description="Wav2Vec2 deepfake-audio verdict (Phase 3).",
    )
    synthetic_audio_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    detection_details: Optional[AudioDetectionOutput] = Field(
        None,
        description="Detailed synthetic-audio detector output with window scores and class probabilities.",
    )
    av_sync_ok: Optional[bool] = Field(
        None,
        description="SyncNet A/V sync check (optional, None if not run).",
    )
    error: Optional[str] = None
