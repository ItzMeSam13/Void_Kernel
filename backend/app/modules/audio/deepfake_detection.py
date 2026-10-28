"""
Module 4 — Audio Forensics: Synthetic-Audio Detection Sub-component (Person 3).

Uses a fine-tuned Wav2Vec2 audio classification model:
    `mo-thecreator/Deepfake-audio-detection`

Public entrypoints:
    run(input: AudioDetectionInput) -> AudioDetectionOutput
    detect_deepfake_audio(audio_path, ...) -> AudioDetectionOutput

Architecture & Design decisions (traceable to architecture.md §Module 4, §6):
- **Contract-first**: typed Pydantic input and output schemas.
- **Singleton model lifecycle**: Model and FeatureExtractor are loaded lazily
  once per process and reused across requests. Protected by threading.Lock.
- **Dynamic label mapping**: validates id2label/label2id configuration at runtime
  without hardcoding index assumptions.
- **Dynamic sample rate**: reads expected sampling rate (16 kHz) directly from
  the feature extractor / processor config.
- **Long audio chunking**: slices long recordings into temporal windows without
  silent truncation, preserving start/end timestamps and per-window scores.
- **Silence & anomaly gating**: identifies silence or invalid audio energy, returning
  inconclusive/not_assessed status rather than misleading classifications.
- **Authenticity signal, not verdict**: returns calibrated class probabilities alongside
  qualified signal labels ('synthetic_audio_signal_detected', 'no_strong_signal_detected',
  'inconclusive', 'not_assessed').
"""
from __future__ import annotations

import logging
import os
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import soundfile as sf
import torch
from transformers import AutoFeatureExtractor, AutoModelForAudioClassification

from app.modules.audio.contracts import (
    AudioDetectionInput,
    AudioDetectionOutput,
    AudioSignal,
    AudioWindowScore,
    DetectionStatus,
)

logger = logging.getLogger(__name__)

# ── Configuration defaults ──────────────────────────────────────────────────

_DEFAULT_MODEL_ID: str = "mo-thecreator/Deepfake-audio-detection"
_DEFAULT_DEVICE: str = "auto"
_DEFAULT_THRESHOLD: float = 0.65
_DEFAULT_WINDOW_SEC: float = 5.0
_DEFAULT_OVERLAP_SEC: float = 1.0
_MIN_AUDIO_DURATION_SEC: float = 0.25
_SILENCE_RMS_THRESHOLD: float = 1e-4

# ── Singleton model state ───────────────────────────────────────────────────

_model: Optional[AutoModelForAudioClassification] = None
_feature_extractor: Optional[AutoFeatureExtractor] = None
_device: Optional[str] = None
_loaded_model_id: Optional[str] = None
_lock = threading.Lock()


def _get_config_value(attr_name: str, fallback: Union[str, float]) -> Union[str, float]:
    """Read configuration from app.core.config.settings, environment var, or fallback."""
    env_val = os.environ.get(attr_name)
    if env_val is not None:
        if isinstance(fallback, float):
            try:
                return float(env_val)
            except ValueError:
                pass
            return fallback
        return env_val
    try:
        from app.core.config import settings
        val = getattr(settings, attr_name, None)
        if val is not None:
            return val
    except Exception:
        pass
    return fallback


def _resolve_device(requested_device: Optional[str] = None) -> str:
    """Select appropriate device ('cuda' if available and requested, else 'cpu')."""
    dev = (requested_device or _get_config_value("DEEPFAKE_AUDIO_DEVICE", _DEFAULT_DEVICE)).lower()
    if dev == "cuda" and torch.cuda.is_available():
        return "cuda"
    if dev == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    return "cpu"


def _get_cache_dir() -> Optional[str]:
    """Determine Hugging Face cache directory."""
    return os.environ.get("HF_HOME") or os.environ.get("TRANSFORMERS_CACHE")


def get_model(
    model_id: Optional[str] = None,
    device: Optional[str] = None,
) -> Tuple[AutoModelForAudioClassification, AutoFeatureExtractor, str]:
    """
    Retrieve or initialize singleton Wav2Vec2 model and feature extractor.
    Thread-safe and cached across requests.
    """
    global _model, _feature_extractor, _device, _loaded_model_id

    target_id = model_id or str(_get_config_value("DEEPFAKE_AUDIO_MODEL_ID", _DEFAULT_MODEL_ID))
    target_dev = _resolve_device(device)

    with _lock:
        if (
            _model is not None
            and _feature_extractor is not None
            and _loaded_model_id == target_id
            and _device == target_dev
        ):
            return _model, _feature_extractor, _device

        logger.info(
            "Loading Wav2Vec2 audio detection model '%s' (device=%s)...",
            target_id,
            target_dev,
        )
        cache_dir = _get_cache_dir()

        fe = AutoFeatureExtractor.from_pretrained(target_id, cache_dir=cache_dir)
        m = AutoModelForAudioClassification.from_pretrained(target_id, cache_dir=cache_dir)
        m.to(target_dev)
        m.eval()

        _model = m
        _feature_extractor = fe
        _device = target_dev
        _loaded_model_id = target_id

        return _model, _feature_extractor, _device


def reset_model() -> None:
    """Reset the singleton model instance (primarily for testing and mocking)."""
    global _model, _feature_extractor, _device, _loaded_model_id
    with _lock:
        _model = None
        _feature_extractor = None
        _device = None
        _loaded_model_id = None


def _resolve_label_indices(id2label: Dict[Union[int, str], str]) -> Tuple[int, int]:
    """
    Determine the class indices for 'fake' and 'real' from model's id2label mapping.
    Raises ValueError if configuration is malformed or missing expected classes.
    """
    fake_idx: Optional[int] = None
    real_idx: Optional[int] = None

    for k, v in id2label.items():
        idx = int(k)
        label_lower = str(v).lower()
        if "fake" in label_lower or "synth" in label_lower:
            fake_idx = idx
        elif "real" in label_lower or "bona" in label_lower:
            real_idx = idx

    if fake_idx is None or real_idx is None:
        raise ValueError(
            f"Cannot resolve 'fake' and 'real' classes from model id2label: {id2label}"
        )

    return fake_idx, real_idx


def _load_and_resample_audio(audio_path: Union[str, Path], target_sr: int) -> Tuple[np.ndarray, float]:
    """
    Load an audio file, convert to mono, resample to target_sr, and check validity.
    Returns:
        (waveform_1d_float32, duration_sec)
    """
    path = Path(audio_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {path}")
    if not path.is_file():
        raise ValueError(f"Audio path is not a file: {path}")
    if path.stat().st_size == 0:
        raise ValueError(f"Audio file is empty (0 bytes): {path}")

    # Read audio using soundfile (supports WAV, MP3, FLAC, OGG, etc.)
    data, orig_sr = sf.read(str(path), dtype="float32")

    # Convert multichannel to mono
    if data.ndim > 1:
        data = np.mean(data, axis=1)

    # Check finite numbers
    if not np.all(np.isfinite(data)):
        raise ValueError("Audio waveform contains non-finite values (NaN or Inf).")

    # Resample if sample rate doesn't match model expected rate
    if orig_sr != target_sr:
        try:
            import scipy.signal
            target_length = int(round(len(data) * float(target_sr) / float(orig_sr)))
            data = scipy.signal.resample(data, target_length)
        except Exception:
            try:
                import librosa
                data = librosa.resample(data, orig_sr=orig_sr, target_sr=target_sr)
            except Exception as resample_err:
                raise RuntimeError(
                    f"Failed to resample audio from {orig_sr}Hz to {target_sr}Hz: {resample_err}"
                ) from resample_err

    duration_sec = float(len(data)) / float(target_sr)
    return data.astype(np.float32), duration_sec


def _classify_waveform_chunk(
    chunk: np.ndarray,
    model: AutoModelForAudioClassification,
    feature_extractor: AutoFeatureExtractor,
    device: str,
    target_sr: int,
    fake_idx: int,
    real_idx: int,
) -> Tuple[float, float]:
    """
    Run forward pass on a single 1D waveform slice.
    Returns (fake_probability, real_probability).
    """
    inputs = feature_extractor(
        chunk,
        sampling_rate=target_sr,
        return_tensors="pt",
    )
    input_values = inputs["input_values"].to(device)

    with torch.no_grad():
        outputs = model(input_values=input_values)
        logits = outputs.logits

    if not torch.all(torch.isfinite(logits)):
        raise ValueError("Model produced non-finite logits (NaN/Inf).")

    probs = torch.softmax(logits, dim=-1).squeeze(0).cpu().numpy()

    fake_prob = float(probs[fake_idx])
    real_prob = float(probs[real_idx])

    # Re-normalize just in case
    total = fake_prob + real_prob
    if total > 0:
        fake_prob /= total
        real_prob /= total

    return fake_prob, real_prob


def run(input: AudioDetectionInput) -> AudioDetectionOutput:
    """
    Canonical Module 4 synthetic-audio detection entrypoint per architecture.md §6.

    Parameters
    ----------
    input : AudioDetectionInput
        Contains audio_path, optional classification threshold, and window settings.

    Returns
    -------
    AudioDetectionOutput
        Structured synthetic-audio findings, including raw probabilities,
        qualified signal verdict, audio duration, and temporal window breakdown.
    """
    model_id = input.model_id or str(_get_config_value("DEEPFAKE_AUDIO_MODEL_ID", _DEFAULT_MODEL_ID))
    threshold = (
        input.threshold
        if input.threshold is not None
        else float(_get_config_value("DEEPFAKE_AUDIO_THRESHOLD", _DEFAULT_THRESHOLD))
    )
    window_sec = (
        input.window_duration_sec
        if input.window_duration_sec is not None
        else float(_get_config_value("DEEPFAKE_AUDIO_WINDOW_SEC", _DEFAULT_WINDOW_SEC))
    )
    overlap_sec = (
        input.window_overlap_sec
        if input.window_overlap_sec is not None
        else float(_get_config_value("DEEPFAKE_AUDIO_OVERLAP_SEC", _DEFAULT_OVERLAP_SEC))
    )

    # ── 1. Validate audio input file existence ───────────────────────────────
    try:
        path = Path(input.audio_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {path}")
        if not path.is_file():
            raise ValueError(f"Audio path is not a file: {path}")
        if path.stat().st_size == 0:
            raise ValueError(f"Audio file is empty (0 bytes): {path}")
    except (FileNotFoundError, ValueError) as exc:
        return AudioDetectionOutput(
            status=DetectionStatus.ERROR,
            verdict="not_assessed",
            model_id=model_id,
            error_message=str(exc),
        )
    except Exception as exc:
        return AudioDetectionOutput(
            status=DetectionStatus.ERROR,
            verdict="not_assessed",
            model_id=model_id,
            error_message=f"Invalid audio path {input.audio_path}: {exc}",
        )

    # ── 2. Load model & feature extractor ────────────────────────────────────
    try:
        model, feature_extractor, device = get_model(model_id=model_id)
        target_sr = getattr(feature_extractor, "sampling_rate", 16000)
        id2label = getattr(model.config, "id2label", {0: "fake", 1: "real"})
        fake_idx, real_idx = _resolve_label_indices(id2label)
    except Exception as exc:
        logger.exception("Failed to initialize Wav2Vec2 model %s", model_id)
        return AudioDetectionOutput(
            status=DetectionStatus.ERROR,
            verdict="not_assessed",
            model_id=model_id,
            error_message=f"Model initialization failed: {exc}",
        )

    # ── 3. Load and preprocess audio ─────────────────────────────────────────
    try:
        waveform, duration = _load_and_resample_audio(path, target_sr)
    except (FileNotFoundError, ValueError) as exc:
        return AudioDetectionOutput(
            status=DetectionStatus.ERROR,
            verdict="not_assessed",
            model_id=model_id,
            error_message=str(exc),
        )
    except Exception as exc:
        logger.exception("Audio loading/preprocessing failed for %s", input.audio_path)
        return AudioDetectionOutput(
            status=DetectionStatus.ERROR,
            verdict="not_assessed",
            model_id=model_id,
            error_message=f"Audio decoding failed: {exc}",
        )

    # ── 4. Validate audio duration and energy (silence / short audio) ─────────
    if duration < _MIN_AUDIO_DURATION_SEC:
        return AudioDetectionOutput(
            status=DetectionStatus.NOT_ASSESSED,
            verdict="not_assessed",
            audio_duration=duration,
            model_id=model_id,
            error_message=f"Audio duration ({duration:.2f}s) is too short for inference (< {_MIN_AUDIO_DURATION_SEC}s).",
        )

    rms = float(np.sqrt(np.mean(waveform ** 2)))
    peak = float(np.max(np.abs(waveform)))
    if rms < _SILENCE_RMS_THRESHOLD or peak < _SILENCE_RMS_THRESHOLD:
        return AudioDetectionOutput(
            status=DetectionStatus.SILENCE_OR_EMPTY,
            verdict="inconclusive",
            synthetic_audio_confidence=0.0,
            fake_score=None,
            real_score=None,
            audio_duration=duration,
            model_id=model_id,
            error_message="Audio signal is silent or near-zero amplitude; cannot assess authenticity.",
        )

    # ── 5. Chunked inference for bounded memory on long recordings ───────────
    window_samples = int(round(window_sec * target_sr))
    step_samples = max(1, int(round((window_sec - overlap_sec) * target_sr)))

    window_scores: List[AudioWindowScore] = []
    total_samples = len(waveform)

    try:
        if total_samples <= window_samples:
            # Short recording: process as a single full-window pass
            f_prob, r_prob = _classify_waveform_chunk(
                waveform, model, feature_extractor, device, target_sr, fake_idx, real_idx
            )
            pred_lbl = "fake" if f_prob >= 0.5 else "real"
            window_scores.append(
                AudioWindowScore(
                    start_sec=0.0,
                    end_sec=round(duration, 3),
                    fake_score=round(f_prob, 4),
                    real_score=round(r_prob, 4),
                    predicted_label=pred_lbl,
                )
            )
        else:
            # Long recording: sliding temporal windows
            start_idx = 0
            while start_idx < total_samples:
                end_idx = min(start_idx + window_samples, total_samples)
                chunk = waveform[start_idx:end_idx]

                # If final partial chunk is too short (< 0.5s), don't introduce distortion
                if len(chunk) < int(target_sr * 0.5) and window_scores:
                    break

                win_start_sec = round(start_idx / target_sr, 3)
                win_end_sec = round(end_idx / target_sr, 3)

                f_prob, r_prob = _classify_waveform_chunk(
                    chunk, model, feature_extractor, device, target_sr, fake_idx, real_idx
                )
                pred_lbl = "fake" if f_prob >= 0.5 else "real"
                window_scores.append(
                    AudioWindowScore(
                        start_sec=win_start_sec,
                        end_sec=win_end_sec,
                        fake_score=round(f_prob, 4),
                        real_score=round(r_prob, 4),
                        predicted_label=pred_lbl,
                    )
                )

                if end_idx >= total_samples:
                    break
                start_idx += step_samples

    except Exception as exc:
        logger.exception("Wav2Vec2 inference failed on %s", input.audio_path)
        return AudioDetectionOutput(
            status=DetectionStatus.ERROR,
            verdict="not_assessed",
            audio_duration=duration,
            model_id=model_id,
            error_message=f"Model inference failed: {exc}",
        )

    # ── 6. Aggregate temporal scores ─────────────────────────────────────────
    # Summary calculation:
    # A manipulated audio track may be partially spliced (cloned speech for a few seconds).
    # We blend the maximum window fake score (60%) with the mean window fake score (40%).
    if len(window_scores) == 1:
        agg_fake = window_scores[0].fake_score
    else:
        peak_fake = max(w.fake_score for w in window_scores)
        mean_fake = float(np.mean([w.fake_score for w in window_scores]))
        agg_fake = 0.60 * peak_fake + 0.40 * mean_fake

    agg_fake = float(np.clip(agg_fake, 0.0, 1.0))
    agg_real = float(np.clip(1.0 - agg_fake, 0.0, 1.0))
    pred_label = "fake" if agg_fake >= 0.5 else "real"

    # ── 7. Map to qualified authenticity signal (Interpretation Policy) ─────
    # - agg_fake >= threshold (default 0.65) -> synthetic_audio_signal_detected
    # - agg_fake < (1.0 - threshold, e.g. 0.35) -> no_strong_signal_detected
    # - ambiguous middle -> inconclusive
    low_threshold = 1.0 - threshold
    if agg_fake >= threshold:
        verdict: AudioSignal = "synthetic_audio_signal_detected"
        confidence = agg_fake
    elif agg_fake < low_threshold:
        verdict = "no_strong_signal_detected"
        confidence = agg_real
    else:
        verdict = "inconclusive"
        confidence = round(1.0 - 2.0 * abs(agg_fake - 0.5), 4)

    return AudioDetectionOutput(
        status=DetectionStatus.SUCCESS,
        verdict=verdict,
        synthetic_audio_confidence=round(confidence, 4),
        fake_score=round(agg_fake, 4),
        real_score=round(agg_real, 4),
        class_probabilities={
            "fake": round(agg_fake, 4),
            "real": round(agg_real, 4),
        },
        predicted_label=pred_label,
        audio_duration=round(duration, 3),
        model_id=model_id,
        window_scores=window_scores,
    )


def detect_deepfake_audio(
    audio_path: Union[str, Path],
    threshold: Optional[float] = None,
    window_duration_sec: Optional[float] = None,
    window_overlap_sec: Optional[float] = None,
    model_id: Optional[str] = None,
) -> AudioDetectionOutput:
    """
    Convenience wrapper for callers providing plain arguments.

    Parameters
    ----------
    audio_path : str or Path
        Path to the local audio file.
    threshold : Optional[float]
        Optional classification threshold for synthetic verdict.
    window_duration_sec : Optional[float]
        Window duration in seconds for long audio chunking.
    window_overlap_sec : Optional[float]
        Window overlap in seconds.
    model_id : Optional[str]
        Optional model checkpoint override.

    Returns
    -------
    AudioDetectionOutput
        Structured synthetic-audio findings.
    """
    return run(
        AudioDetectionInput(
            audio_path=str(audio_path),
            threshold=threshold,
            window_duration_sec=window_duration_sec,
            window_overlap_sec=window_overlap_sec,
            model_id=model_id,
        )
    )
