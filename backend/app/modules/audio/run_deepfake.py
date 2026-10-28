#!/usr/bin/env python3
"""
Standalone Wav2Vec2 synthetic-audio detection runner — real-model smoke test.

Invokes the deepfake audio detection module directly against a local
audio file, without FastAPI, LangGraph, Redis, Supabase, or external services.

Usage
-----
From the backend directory (or inside the Docker container)::

    # Using a real audio file:
    python -m app.modules.audio.run_deepfake --audio /path/to/speech.wav

    # Using a real audio file with a custom threshold:
    python -m app.modules.audio.run_deepfake --audio /path/to/speech.mp3 --threshold 0.70

    # Using an auto-generated synthetic test audio file:
    python -m app.modules.audio.run_deepfake
"""
from __future__ import annotations

import argparse
import json
import math
import struct
import sys
import tempfile
import wave
from pathlib import Path

from app.modules.audio.contracts import AudioDetectionInput
from app.modules.audio.deepfake_detection import run


def _create_fallback_audio() -> str:
    """
    Create a 2-second 16kHz mono synthetic test WAV file with a tone (440 Hz)
    and return its temporary file path.
    """
    tmp_dir = Path(tempfile.mkdtemp(prefix="deepfake_smoke_"))
    wav_path = tmp_dir / "test_synthetic_tone.wav"

    sample_rate = 16000
    duration_sec = 2.0
    num_samples = int(sample_rate * duration_sec)

    with wave.open(str(wav_path), "wb") as wav_file:
        wav_file.setnchannels(1)  # mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)

        samples = []
        for i in range(num_samples):
            # 440 Hz sine tone with harmonic
            val = int(12000 * math.sin(2.0 * math.pi * 440.0 * (i / sample_rate)))
            samples.append(val)

        raw_frames = struct.pack("<" + ("h" * len(samples)), *samples)
        wav_file.writeframes(raw_frames)

    print(f"[info] No --audio provided; generated synthetic test audio at: {wav_path}")
    return str(wav_path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Wav2Vec2 synthetic-audio detection (real checkpoint, local inference).",
    )
    parser.add_argument(
        "--audio",
        type=str,
        default=None,
        help="Path to a local audio file (.wav, .mp3, etc.). If omitted, a synthetic audio file is generated.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="Classification threshold for synthetic verdict (0.0 - 1.0). Default: 0.65.",
    )
    parser.add_argument(
        "--model-id",
        type=str,
        default=None,
        help="Hugging Face model checkpoint. Default: mo-thecreator/Deepfake-audio-detection.",
    )

    args = parser.parse_args()

    audio_path = args.audio or _create_fallback_audio()

    print(f"[info] Analyzing audio: {audio_path}")
    print(f"[info] Model: {args.model_id or 'default (mo-thecreator/Deepfake-audio-detection)'}")

    det_input = AudioDetectionInput(
        audio_path=audio_path,
        threshold=args.threshold,
        model_id=args.model_id,
    )

    result = run(det_input)

    print("\n--- Detection Result ---")
    print(json.dumps(result.model_dump(), indent=2))

    if result.status.value == "error":
        print(f"\n[error] Detection failed: {result.error_message}", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"\n[success] Status: {result.status.value}")
        print(f"[verdict] {result.verdict}")
        print(f"[confidence] {result.synthetic_audio_confidence}")
        print(f"[fake_score] {result.fake_score}")


if __name__ == "__main__":
    main()

