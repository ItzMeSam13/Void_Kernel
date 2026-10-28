#!/usr/bin/env python3
"""
Standalone Smaug AI-image detection runner — real-model smoke test.

Invokes the Smaug component directly against a local image, without FastAPI,
LangGraph, Redis, Supabase, or any other service.

Usage
-----
From the backend directory (or inside the Docker container)::

    # Using a real image file:
    python -m app.modules.image.run_smaug --image /path/to/photo.jpg

    # Using a generated test image (created automatically):
    python -m app.modules.image.run_smaug

    # With a custom detection threshold:
    python -m app.modules.image.run_smaug --image /path/to/photo.jpg --threshold 0.7

If ``--image`` is omitted, a small synthetic 128×128 green PNG is created in a
temporary directory and used for the test.

The model weights will be downloaded on first run (≈1 GB for
``abacusai/Smaug-AI-Image-Detector``).  Subsequent runs reuse the Hugging Face
cache.

Note: A low score on a synthetic test image is expected — the solid-colour image
is visually trivial and does not represent a realistic real-world input.  Use a
real photograph or AI-generated image for meaningful smoke testing.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path


def _create_fallback_image() -> str:
    """Create a small green test image and return its path."""
    from PIL import Image  # Lazy import — Pillow lives inside the Docker container.

    tmp_dir = Path(tempfile.mkdtemp(prefix="smaug_smoke_"))
    img_path = tmp_dir / "test_image.png"
    img = Image.new("RGB", (128, 128), color=(0, 180, 50))
    img.save(img_path)
    print(f"[info] No --image provided; generated synthetic test image at {img_path}")
    print("[info] NOTE: Smaug score on a solid-colour synthetic image is not meaningful.")
    return str(img_path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Smaug AI-image detection (real model, local inference).",
    )
    parser.add_argument(
        "--image",
        type=str,
        default=None,
        help="Path to a local image file.  If omitted, a synthetic test image is generated.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help=(
            "Detection threshold for the optional label field [0.0, 1.0].  "
            "Default 0.5 (from model card).  This is NOT universally optimal — "
            "treat the raw ai_probability as the primary signal."
        ),
    )
    args = parser.parse_args()

    # Lazy-import so --help is instant even if torch isn't installed.
    from app.modules.image.contracts import SmaugDetectionInput
    from app.modules.image.ai_detect import run

    image_path = args.image or _create_fallback_image()

    print(f"\n{'=' * 60}")
    print(f" Smaug AI-Image Detection — Smoke Test")
    print(f"{'=' * 60}")
    print(f" Image     : {image_path}")
    print(f" Threshold : {args.threshold}")
    print(f"{'=' * 60}\n")
    print("[info] Loading Smaug model (first run downloads ~1 GB) …\n")

    inp = SmaugDetectionInput(image_path=image_path, detection_threshold=args.threshold)
    result = run(inp)

    print(json.dumps(json.loads(result.model_dump_json()), indent=2))

    if result.status.value != "success":
        print(f"\n[FAIL] Status: {result.status.value}", file=sys.stderr)
        sys.exit(1)

    print(f"\n[OK] AI-generated probability : {result.ai_probability}")
    print(f"[OK] Label (threshold={args.threshold}) : {result.label}")
    print(
        "\n[note] This score is a signal, not a verdict.  "
        "A low score does NOT prove the image is genuine."
    )


if __name__ == "__main__":
    main()

