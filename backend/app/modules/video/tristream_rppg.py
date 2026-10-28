"""
Module 3 — Task 3: rPPG Biometric Pulse Extraction.

Principle: "Deepfakes are biologically dead."
Real videos contain micro-fluctuations in forehead skin colour corresponding
to the human heartbeat (remote photoplethysmography, rPPG). Synthetically
generated faces lack this signal because:
  - Diffusion / GAN models generate each frame independently — no temporal
    physiological constraint.
  - Face-swap composites may preserve overall brightness but lose the subtle
    periodic green-channel oscillation tied to blood-volume pulses.

Pipeline:
  1. For each snippet, re-seek the video to the snippet's start frame and
     extract the forehead region using MediaPipe landmarks.
  2. Collect the mean Green-channel value per frame → green signal time-series.
  3. Detrend (subtract mean) → apply Butterworth bandpass 0.7–2.5 Hz (42–150 BPM).
  4. FFT → find dominant peak in the physiological band.
  5. SNR (peak / band-mean) above threshold → pulse present → no deepfake signal.
     SNR below threshold → no clear pulse → deepfake biometric evidence.

Note: verdict naming (stream_verdict) follows StreamVerdict convention:
  "signal_detected"        = deepfake signal found (no pulse)
  "no_strong_signal_detected" = real physiological pulse present
  "inconclusive"           = insufficient frames or ambiguous SNR
  "not_assessed"           = no face detected / FPS unreadable
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import cv2
import mediapipe as mp
import numpy as np
from scipy import signal as sp_signal

from app.modules.video.contracts import SnippetMeta

logger = logging.getLogger(__name__)

# Forehead landmark indices (MediaPipe FaceMesh 468-point model).
# This ring covers the upper-forehead region where skin colour is stable
# and hair / eyebrow occlusion is minimal.
_FOREHEAD_LM = [10, 67, 69, 104, 108, 151, 337, 299, 297, 338]

_RPPG_LOW_HZ = 0.7     # 42 BPM
_RPPG_HIGH_HZ = 2.5    # 150 BPM
_MIN_FRAMES = 15        # below this we cannot reliably bandpass + FFT
_PULSE_SNR_THRESHOLD = 2.5   # peak / band-mean ratio that counts as "pulse present"


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------

@dataclass
class RppgResult:
    biometric_pulse_detected: Optional[bool]   # None when not_assessed
    rppg_peak_hz: Optional[float]              # dominant frequency or None
    stream_verdict: str                         # StreamVerdict string value


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _forehead_roi(
    frame_bgr: np.ndarray,
    landmarks,
    img_h: int,
    img_w: int,
) -> Optional[np.ndarray]:
    xs = [int(landmarks[i].x * img_w) for i in _FOREHEAD_LM if i < len(landmarks)]
    ys = [int(landmarks[i].y * img_h) for i in _FOREHEAD_LM if i < len(landmarks)]
    if not xs or not ys:
        return None
    x1 = max(0, min(xs) - 4)
    y1 = max(0, min(ys) - 4)
    x2 = min(img_w, max(xs) + 4)
    y2 = min(img_h, max(ys) + 4)
    roi = frame_bgr[y1:y2, x1:x2]
    return roi if roi.size > 0 else None


def _bandpass_fft(
    green_signal: np.ndarray,
    fps: float,
) -> tuple[Optional[float], float]:
    """
    Apply Butterworth bandpass and FFT.
    Returns (dominant_hz, snr) where snr = peak_power / band_mean_power.
    """
    nyq = fps / 2.0
    low_n = _RPPG_LOW_HZ / nyq
    high_n = _RPPG_HIGH_HZ / nyq

    if not (0 < low_n < high_n < 1):
        return None, 0.0

    try:
        b, a = sp_signal.butter(3, [low_n, high_n], btype="band")
        filtered = sp_signal.filtfilt(b, a, green_signal)
    except Exception as exc:
        logger.warning("rPPG bandpass failed: %s", exc)
        return None, 0.0

    fft_vals = np.abs(np.fft.rfft(filtered))
    freqs = np.fft.rfftfreq(len(filtered), d=1.0 / fps)

    band_mask = (freqs >= _RPPG_LOW_HZ) & (freqs <= _RPPG_HIGH_HZ)
    if not np.any(band_mask):
        return None, 0.0

    band_vals = fft_vals[band_mask]
    band_freqs = freqs[band_mask]
    peak_idx = int(np.argmax(band_vals))

    peak_hz = float(band_freqs[peak_idx])
    snr = float(band_vals[peak_idx]) / (float(np.mean(band_vals)) + 1e-8)

    return peak_hz, snr


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze_rppg(
    video_path: Path,
    snippet_metas: list[SnippetMeta],
    fps: float,
) -> RppgResult:
    """
    Extract forehead green-channel signal and detect physiological pulse.

    Re-seeks the video to each snippet's start_frame to avoid storing all frames
    in memory (consistent with Phase 1's bounded-memory design).
    """
    cap = cv2.VideoCapture(str(video_path))
    face_mesh = mp.solutions.face_mesh.FaceMesh(
        static_image_mode=True,
        max_num_faces=1,
        refine_landmarks=False,
        min_detection_confidence=0.4,
    )

    green_series: list[float] = []

    for meta in snippet_metas:
        if not meta.face_detected:
            continue

        cap.set(cv2.CAP_PROP_POS_FRAMES, meta.start_frame)
        n_frames = meta.end_frame - meta.start_frame + 1

        for _ in range(n_frames):
            ok, frame_bgr = cap.read()
            if not ok:
                break

            img_h, img_w = frame_bgr.shape[:2]
            rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            result = face_mesh.process(rgb)

            if not result.multi_face_landmarks:
                continue

            landmarks = result.multi_face_landmarks[0].landmark
            roi = _forehead_roi(frame_bgr, landmarks, img_h, img_w)
            if roi is not None:
                # Green channel is index 1 in BGR
                green_series.append(float(np.mean(roi[:, :, 1])))

    cap.release()
    face_mesh.close()

    if len(green_series) < _MIN_FRAMES:
        msg = f"rPPG: only {len(green_series)} forehead frames collected (need {_MIN_FRAMES}) — not_assessed."
        logger.info(msg)
        return RppgResult(None, None, "not_assessed")

    arr = np.array(green_series, dtype=np.float64)
    arr -= arr.mean()   # detrend: remove slow illumination drift

    peak_hz, snr = _bandpass_fft(arr, fps)

    pulse_detected = snr >= _PULSE_SNR_THRESHOLD

    logger.info(
        "rPPG: frames=%d peak_hz=%.3f snr=%.2f pulse=%s",
        len(green_series),
        peak_hz if peak_hz else 0.0,
        snr,
        pulse_detected,
    )

    # Deepfake signal = absence of pulse
    if pulse_detected:
        verdict = "no_strong_signal_detected"   # real physiological signal → no deepfake evidence
    else:
        verdict = "signal_detected"              # no pulse → biometric deepfake evidence

    return RppgResult(
        biometric_pulse_detected=pulse_detected,
        rppg_peak_hz=round(peak_hz, 3) if peak_hz else None,
        stream_verdict=verdict,
    )
