"""
Module 4 — Audio Forensics: Speech Transcription Sub-component (Person 3).

Uses faster-whisper (CTranslate2-backed Whisper) for efficient local speech
transcription without per-minute cloud API fees.

Public entrypoints:
    run(input: AudioTranscriptionInput) -> AudioTranscriptionOutput
    transcribe_audio(audio_path, language=None, model_size=None) -> AudioTranscriptionOutput

Architecture & Design decisions (traceable to architecture.md §Module 4 and §6):
- **Contract-first**: typed Pydantic input and output schemas.
- **Singleton model lifecycle**: WhisperModel is loaded lazily once per process
  and reused across subsequent requests. Thread-safe with threading.Lock.
- **Device & compute selection**: CUDA with float16 when available; CPU with
  int8/default fallback. Never assumes GPU presence in Docker.
- **Task**: transcription only (task="transcribe"), preserving spoken language
  without translation.
- **Lazy generator materialization**: faster-whisper returns a generator; this
  module explicitly consumes and normalizes all segments before returning.
- **Fail honest**: clearly distinguishes between valid audio with no speech
  (status="no_speech_detected") and genuine errors (status="error").
- **Zero cross-module coupling**: no dependencies on video preprocessing,
  LangGraph state, or external services.
"""
from __future__ import annotations

import logging
import os
import threading
from pathlib import Path
from typing import List, Optional, Tuple, Union

try:
    import ctranslate2
except ImportError:
    ctranslate2 = None

from faster_whisper import WhisperModel

from app.modules.audio.contracts import (
    AudioTranscriptionInput,
    AudioTranscriptionOutput,
    TranscriptSegment,
    TranscriptionStatus,
)

logger = logging.getLogger(__name__)

# ── Configuration defaults ──────────────────────────────────────────────────

_DEFAULT_MODEL_SIZE: str = "small"
_DEFAULT_DEVICE: str = "auto"
_DEFAULT_COMPUTE_TYPE: str = "default"

# ── Singleton model state ───────────────────────────────────────────────────

_model: Optional[WhisperModel] = None
_loaded_model_size: Optional[str] = None
_loaded_device: Optional[str] = None
_loaded_compute_type: Optional[str] = None
_lock = threading.Lock()


def _get_config_value(attr_name: str, fallback: str) -> str:
    """Read a setting from app.core.config.settings, environment var, or fallback."""
    env_val = os.environ.get(attr_name)
    if env_val:
        return env_val
    try:
        from app.core.config import settings
        val = getattr(settings, attr_name, None)
        if val:
            return str(val)
    except Exception:
        pass
    return fallback


def _get_download_root() -> Optional[str]:
    """Determine the cache directory for faster-whisper models."""
    root = os.environ.get("WHISPER_DOWNLOAD_ROOT")
    if root:
        return root
    try:
        from app.core.config import settings
        if settings.WHISPER_DOWNLOAD_ROOT:
            return str(settings.WHISPER_DOWNLOAD_ROOT)
    except Exception:
        pass
    # Reuse HF_HOME / TRANSFORMERS_CACHE if set (e.g. Docker volume)
    hf_home = os.environ.get("HF_HOME") or os.environ.get("TRANSFORMERS_CACHE")
    if hf_home:
        return os.path.join(hf_home, "hub")
    return None


def _resolve_device_and_compute_type(
    requested_device: Optional[str] = None,
    requested_compute_type: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Select supported device and compatible compute_type.
    Ensures CPU runs with int8/float32 (not float16, which crashes CTranslate2 on CPU).
    """
    device = (requested_device or _get_config_value("WHISPER_DEVICE", _DEFAULT_DEVICE)).lower()
    compute_type = (
        requested_compute_type or _get_config_value("WHISPER_COMPUTE_TYPE", _DEFAULT_COMPUTE_TYPE)
    ).lower()

    cuda_available = False
    if ctranslate2 is not None:
        try:
            cuda_available = ctranslate2.get_cuda_device_count() > 0
        except Exception:
            cuda_available = False
    else:
        try:
            import torch
            cuda_available = torch.cuda.is_available()
        except ImportError:
            cuda_available = False

    if device == "cuda" and not cuda_available:
        logger.warning("CUDA requested for faster-whisper, but no CUDA device found. Falling back to CPU.")
        device = "cpu"
    elif device == "auto":
        device = "cuda" if cuda_available else "cpu"

    # CPU safety check: CTranslate2 raises ValueError if float16 is passed on CPU
    if device == "cpu":
        if compute_type in ("float16", "default"):
            compute_type = "int8"
    elif device == "cuda":
        if compute_type == "default":
            compute_type = "float16"

    return device, compute_type


def get_model(
    model_size: Optional[str] = None,
    device: Optional[str] = None,
    compute_type: Optional[str] = None,
) -> WhisperModel:
    """
    Retrieve or initialize the singleton WhisperModel instance.
    Thread-safe and cached across requests.
    """
    global _model, _loaded_model_size, _loaded_device, _loaded_compute_type

    target_size = model_size or _get_config_value("WHISPER_MODEL_SIZE", _DEFAULT_MODEL_SIZE)
    target_device, target_compute = _resolve_device_and_compute_type(device, compute_type)

    with _lock:
        if (
            _model is not None
            and _loaded_model_size == target_size
            and _loaded_device == target_device
            and _loaded_compute_type == target_compute
        ):
            return _model

        download_root = _get_download_root()
        logger.info(
            "Loading faster-whisper model '%s' (device=%s, compute_type=%s, download_root=%s)...",
            target_size,
            target_device,
            target_compute,
            download_root,
        )

        _model = WhisperModel(
            model_size_or_path=target_size,
            device=target_device,
            compute_type=target_compute,
            download_root=download_root,
        )
        _loaded_model_size = target_size
        _loaded_device = target_device
        _loaded_compute_type = target_compute

        return _model


def reset_model() -> None:
    """Reset the singleton model instance (primarily for testing and mocking)."""
    global _model, _loaded_model_size, _loaded_device, _loaded_compute_type
    with _lock:
        _model = None
        _loaded_model_size = None
        _loaded_device = None
        _loaded_compute_type = None


def _validate_audio_path(path_input: Union[str, Path]) -> Path:
    """
    Validate that the audio file exists, is a file, and is non-empty.
    Raises FileNotFoundError or ValueError if validation fails.
    """
    if not path_input:
        raise ValueError("Audio path cannot be empty or None.")

    path = Path(path_input).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {path}")
    if not path.is_file():
        raise ValueError(f"Audio path is not a file: {path}")
    if path.stat().st_size == 0:
        raise ValueError(f"Audio file is empty (0 bytes): {path}")

    return path


def run(input: AudioTranscriptionInput) -> AudioTranscriptionOutput:
    """
    Canonical Module 4 speech transcription entrypoint per architecture.md §6.

    Parameters
    ----------
    input : AudioTranscriptionInput
        Contains audio_path, optional language hint, and optional model_size override.

    Returns
    -------
    AudioTranscriptionOutput
        Structured transcription findings, including full transcript,
        chronological timestamped segments, detected language, and status.
    """
    effective_model_size = input.model_size or _get_config_value("WHISPER_MODEL_SIZE", _DEFAULT_MODEL_SIZE)

    # ── 1. Validate audio input ──────────────────────────────────────────────
    try:
        valid_path = _validate_audio_path(input.audio_path)
    except (FileNotFoundError, ValueError) as exc:
        return AudioTranscriptionOutput(
            status=TranscriptionStatus.ERROR,
            error_message=str(exc),
            model_size=effective_model_size,
        )
    except Exception as exc:  # noqa: BLE001
        return AudioTranscriptionOutput(
            status=TranscriptionStatus.ERROR,
            error_message=f"Invalid audio path {input.audio_path}: {exc}",
            model_size=effective_model_size,
        )

    # ── 2. Load model (thread-safe singleton) ────────────────────────────────
    try:
        model = get_model(model_size=effective_model_size)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to initialize faster-whisper model '%s'", effective_model_size)
        return AudioTranscriptionOutput(
            status=TranscriptionStatus.ERROR,
            error_message=f"Model initialization failed: {exc}",
            model_size=effective_model_size,
        )

    # ── 3. Transcribe speech ─────────────────────────────────────────────────
    try:
        segments_gen, info = model.transcribe(
            str(valid_path),
            language=input.language,
            task="transcribe",
            beam_size=5,
        )
        # Materialize the lazy segment generator completely
        raw_segments = list(segments_gen)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Whisper inference failed on audio %s", valid_path)
        return AudioTranscriptionOutput(
            status=TranscriptionStatus.ERROR,
            error_message=f"Whisper transcription failed: {exc}",
            model_size=effective_model_size,
        )

    # ── 4. Collect and normalize segments ────────────────────────────────────
    segments: List[TranscriptSegment] = []
    transcript_parts: List[str] = []

    for seg in raw_segments:
        text = (seg.text or "").strip()
        if text:
            transcript_parts.append(text)
        
        start_sec = round(float(seg.start), 3)
        end_sec = round(float(seg.end), 3)
        no_speech = (
            round(float(seg.no_speech_prob), 4)
            if getattr(seg, "no_speech_prob", None) is not None
            else None
        )
        try:
            segment_obj = TranscriptSegment(
                start=start_sec,
                end=end_sec,
                text=text,
                no_speech_prob=no_speech,
            )
            segments.append(segment_obj)
        except Exception as exc:
            logger.warning("Skipping malformed segment (%s-%s): %s", start_sec, end_sec, exc)

    full_transcript = " ".join(transcript_parts).strip()
    duration = round(float(info.duration), 3) if getattr(info, "duration", None) is not None else None
    lang_prob = (
        round(float(info.language_probability), 4)
        if getattr(info, "language_probability", None) is not None
        else None
    )
    detected_language = getattr(info, "language", None)

    # ── 5. Handle silence vs successful speech ────────────────────────────────
    if not full_transcript:
        return AudioTranscriptionOutput(
            status=TranscriptionStatus.NO_SPEECH_DETECTED,
            transcript="",
            segments=[],
            language=detected_language,
            language_probability=lang_prob,
            duration=duration,
            model_size=effective_model_size,
        )

    return AudioTranscriptionOutput(
        status=TranscriptionStatus.SUCCESS,
        transcript=full_transcript,
        segments=segments,
        language=detected_language,
        language_probability=lang_prob,
        duration=duration,
        model_size=effective_model_size,
    )


def transcribe_audio(
    audio_path: Union[str, Path],
    language: Optional[str] = None,
    model_size: Optional[str] = None,
) -> AudioTranscriptionOutput:
    """
    Convenience wrapper for callers providing plain arguments.

    Parameters
    ----------
    audio_path : str or Path
        Path to the local audio file.
    language : Optional[str]
        Optional language code hint (e.g. 'en').
    model_size : Optional[str]
        Optional model size override (e.g. 'small', 'tiny').

    Returns
    -------
    AudioTranscriptionOutput
        Structured transcription output.
    """
    return run(
        AudioTranscriptionInput(
            audio_path=str(audio_path),
            language=language,
            model_size=model_size,
        )
    )
