#!/usr/bin/env python3
"""
Standalone speech transcription runner — real-model smoke test.

Invokes the faster-whisper transcription module directly against a local
audio file, without FastAPI, LangGraph, Redis, Supabase, or external services.

Usage
-----
From the backend directory (or inside the Docker container)::

    # Using a real audio file:
    python -m app.modules.audio.run_transcribe --audio /path/to/speech.wav

    # Using a real audio file with language hint and model size:
    python -m app.modules.audio.run_transcribe --audio /path/to/speech.mp3 --language en --model-size small

    # Using an auto-generated synthetic test WAV file (created automatically):
    python -m app.modules.audio.run_transcribe --model-size tiny

If ``--audio`` is omitted, a small synthetic 2-second WAV file is created in a
temporary directory and used for the test.
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

from app.modules.audio.contracts import AudioTranscriptionInput
from app.modules.audio.transcription import run


def _create_fallback_audio() -> str:
    """
    Create a 2-second 16kHz mono synthetic test WAV file with a gentle
    tone (440 Hz) and silence, returning its temporary file path.
    """
    tmp_dir = Path(tempfile.mkdtemp(prefix="whisper_smoke_"))
    wav_path = tmp_dir / "test_synthetic_audio.wav"

    sample_rate = 16000
    duration_sec = 2.0
    num_samples = int(sample_rate * duration_sec)

    with wave.open(str(wav_path), "wb") as wav_file:
        wav_file.setnchannels(1)  # mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)

        # Generate 1 sec 440Hz sine wave + 1 sec silence
        samples = []
        for i in range(num_samples):
            if i < sample_rate:
                # 440 Hz sine tone
                value = int(16000 * math.sin(2.0 * math.pi * 440.0 * (i / sample_rate)))
            else:
                value = 0
            samples.append(value)

        raw_frames = struct.pack("<" + ("h" * len(samples)), *samples)
        wav_file.writeframes(raw_frames)

    print(f"[info] No --audio provided; generated synthetic test audio at: {wav_path}")
    return str(wav_path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run faster-whisper speech transcription (real model, local inference).",
    )
    parser.add_argument(
        "--audio",
        type=str,
        default=None,
        help="Path to a local audio file (.wav, .mp3, etc.). If omitted, a synthetic audio file is generated.",
    )
    parser.add_argument(
        "--language",
        type=str,
        default=None,
        help="Optional ISO language code hint (e.g. 'en', 'es'). Default: auto-detect.",
    )
    parser.add_argument(
        "--model-size",
        type=str,
        default=None,
        help="Whisper model size (e.g. 'tiny', 'small', 'base'). Default: 'small' or project config.",
    )

    args = parser.parse_args()

    audio_path = args.audio or _create_fallback_audio()

    print(f"[info] Transcribing audio: {audio_path}")
    print(f"[info] Model size: {args.model_size or 'default (small)'} | Language hint: {args.language or 'auto'}")

    tx_input = AudioTranscriptionInput(
        audio_path=audio_path,
        language=args.language,
        model_size=args.model_size,
    )

    result = run(tx_input)

    print("\n--- Transcription Result ---")
    print(json.dumps(result.model_dump(), indent=2))

    if result.status.value == "error":
        print(f"\n[error] Transcription failed: {result.error_message}", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"\n[success] Status: {result.status.value}")
        print(f"[transcript] '{result.transcript}'")


if __name__ == "__main__":
    main()

