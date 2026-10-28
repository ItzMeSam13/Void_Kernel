#!/usr/bin/env python3
"""
Standalone CLIP similarity runner — real-model smoke test.

Invokes the CLIP module directly against a local image and text claim,
without FastAPI, LangGraph, Redis, Supabase, or any other service.

Usage
-----
From the backend directory (or inside the Docker container)::

    # Using a real image file:
    python -m app.modules.image.run_clip --image /path/to/photo.jpg --claim "A dog playing in a park"

    # Using a generated test image (created automatically):
    python -m app.modules.image.run_clip --claim "A solid green square"

If ``--image`` is omitted, a small synthetic 128×128 green PNG is created in a
temporary directory and used for the test.

The model weights will be downloaded on first run (≈600 MB for
``openai/clip-vit-base-patch32``).  Subsequent runs reuse the Hugging Face
cache.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

from PIL import Image


def _create_fallback_image() -> str:
    """Create a small green test image and return its path."""
    tmp_dir = Path(tempfile.mkdtemp(prefix="clip_smoke_"))
    img_path = tmp_dir / "test_image.png"
    img = Image.new("RGB", (128, 128), color=(0, 180, 50))
    img.save(img_path)
    print(f"[info] No --image provided; generated test image at {img_path}")
    return str(img_path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run CLIP claim-image similarity (real model, local inference).",
    )
    parser.add_argument(
        "--image",
        type=str,
        default=None,
        help="Path to a local image file.  If omitted, a synthetic test image is generated.",
    )
    parser.add_argument(
        "--claim",
        type=str,
        required=True,
        help="Text claim or description to compare against the image.",
    )
    args = parser.parse_args()

    # Lazy-import so --help is instant even if torch isn't installed.
    from app.modules.image.contracts import ClipSimilarityInput
    from app.modules.image.similarity import run

    image_path = args.image or _create_fallback_image()

    print(f"\n{'=' * 60}")
    print(f" CLIP Similarity — Smoke Test")
    print(f"{'=' * 60}")
    print(f" Image : {image_path}")
    print(f" Claim : {args.claim}")
    print(f"{'=' * 60}\n")

    inp = ClipSimilarityInput(image_path=image_path, claim_text=args.claim)
    result = run(inp)

    print(json.dumps(json.loads(result.model_dump_json()), indent=2))

    if result.status.value != "success":
        print(f"\n[FAIL] Status: {result.status.value}", file=sys.stderr)
        sys.exit(1)

    print(f"\n[OK] Cosine similarity = {result.similarity_score}")
    print(f"[OK] Logits per image  = {result.logits_per_image}")


if __name__ == "__main__":
    main()
