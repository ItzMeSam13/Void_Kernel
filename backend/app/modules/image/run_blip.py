#!/usr/bin/env python3
"""
Standalone BLIP captioning runner — real-model smoke test.

Invokes the BLIP module directly against a local image, without FastAPI,
LangGraph, Redis, Supabase, or any other service.

Usage
-----
From the backend directory (or inside the Docker container)::

    # Using a real image file:
    python -m app.modules.image.run_blip --image /path/to/photo.jpg

    # Using a generated test image (created automatically):
    python -m app.modules.image.run_blip

If ``--image`` is omitted, a small synthetic 128×128 green PNG is created in a
temporary directory and used for the test.

The model weights will be downloaded on first run (≈945 MB for
``Salesforce/blip-image-captioning-base``).  Subsequent runs reuse the Hugging
Face cache.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path


def _create_fallback_image() -> str:
    """Create a small green test image and return its path."""
    try:
        from PIL import Image  # Lazy import — Pillow lives inside the Docker container.
    except ImportError as e:
        raise ImportError("Pillow is required for the BLIP smoke test. Install it via 'pip install pillow' or ensure it's listed in requirements.txt") from e

    tmp_dir = Path(tempfile.mkdtemp(prefix="blip_smoke_"))
    img_path = tmp_dir / "test_image.png"
    img = Image.new("RGB", (128, 128), color=(0, 180, 50))
    img.save(img_path)
    print(f"[info] No --image provided; generated test image at {img_path}")
    return str(img_path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run BLIP image captioning (real model, local inference).",
    )
    parser.add_argument(
        "--image",
        type=str,
        default=None,
        help="Path to a local image file.  If omitted, a synthetic test image is generated.",
    )
    args = parser.parse_args()

    # Lazy-import so --help is instant even if torch isn't installed.
    from app.modules.image.contracts import BlipCaptionInput
    from app.modules.image.caption import run

    image_path = args.image or _create_fallback_image()

    print(f"\n{'=' * 60}")
    print(f" BLIP Captioning — Smoke Test")
    print(f"{'=' * 60}")
    print(f" Image : {image_path}")
    print(f"{'=' * 60}\n")

    inp = BlipCaptionInput(image_path=image_path)
    result = run(inp)

    print(json.dumps(json.loads(result.model_dump_json()), indent=2))

    if result.status.value != "success":
        print(f"\n[FAIL] Status: {result.status.value}", file=sys.stderr)
        sys.exit(1)

    print(f"\n[OK] Caption: {result.caption}")


if __name__ == "__main__":
    main()
