#!/usr/bin/env python3
"""
Standalone analyze_image runner — real-model smoke test for the composition layer.

Invokes ``analyze_image(image_path, claim_text)`` against a local image,
testing the integration of all four sub-components (BLIP, CLIP, PaddleOCR, Smaug)
without FastAPI, LangGraph, Redis, or any external service.

Usage
-----
From the ``backend/`` directory (or inside Docker)::

    # With an external claim (runs BLIP, CLIP, OCR, Smaug):
    python -m app.modules.image.run_analyze_image --image image.png --claim "a cat on a car"

    # Without a claim (CLIP skipped, runs BLIP, OCR, Smaug):
    python -m app.modules.image.run_analyze_image --image imagecopy1.png
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Fix Windows C++ DLL order: ensure PyTorch loads before Paddle
try:
    import torch  # noqa: F401
except ImportError:
    pass

# Ensure PaddlePaddle oneDNN flags are set
os.environ["FLAGS_use_mkldnn"] = "0"
os.environ["FLAGS_use_onednn"] = "0"
os.environ["PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT"] = "0"
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

from app.modules.image.analyze_image import analyze_image


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the Module 2 analyze_image composition layer on an image."
    )
    parser.add_argument(
        "--image",
        type=str,
        required=True,
        help="Path to the image file to analyze.",
    )
    parser.add_argument(
        "--claim",
        type=str,
        default=None,
        help="Optional external claim text to compare with the image via CLIP.",
    )

    args = parser.parse_args()

    image_path = Path(args.image)
    if not image_path.exists():
        print(f"[ERROR] Image path does not exist: {image_path}", file=sys.stderr)
        sys.exit(1)

    print("=" * 60)
    print(" Module 2 — Image Intelligence: analyze_image Smoke Test")
    print("=" * 60)
    print(f" Image : {image_path.resolve()}")
    print(f" Claim : {args.claim or '(none — CLIP will be skipped)'}")
    print("=" * 60)
    print()

    findings = analyze_image(str(image_path), claim_text=args.claim)

    print(findings.model_dump_json(indent=2))
    print()
    print("=" * 60)
    print(" Summary:")
    print(f"  BLIP   : {findings.blip.status.value if findings.blip else 'not attempted'}")
    if findings.blip and findings.blip.caption:
        print(f"           Caption: {findings.blip.caption}")

    print(f"  CLIP   : {findings.clip.status.value if findings.clip else f'skipped ({findings.clip_skipped_reason.value if findings.clip_skipped_reason else None})'}")
    if findings.clip and findings.clip.similarity_score is not None:
        print(f"           Score: {findings.clip.similarity_score}")

    print(f"  OCR    : {findings.ocr.status.value if findings.ocr else 'not attempted'}")
    if findings.ocr and findings.ocr.combined_text:
        print(f"           Text: {findings.ocr.combined_text[:80]}...")

    print(f"  Smaug  : {findings.smaug.status.value if findings.smaug else 'not attempted'}")
    if findings.smaug and findings.smaug.ai_probability is not None:
        print(f"           AI Prob: {findings.smaug.ai_probability} ({findings.smaug.label})")
    print("=" * 60)


if __name__ == "__main__":
    main()

