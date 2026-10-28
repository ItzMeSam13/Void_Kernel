#!/usr/bin/env python3
"""
Standalone PaddleOCR text extraction runner — real-model smoke test.

Invokes the PaddleOCR component directly against a local image, without
FastAPI, LangGraph, Redis, Supabase, or any other service.

Usage
-----
From the backend directory (or inside the Docker container)::

    # Run on an image with embedded text (meme, screenshot, sign, poster):
    python -m app.modules.image.run_ocr --image path/to/meme.png

    # Run on an image without text (should return 'no_text_detected'):
    python -m app.modules.image.run_ocr --image path/to/photo.jpg

    # Using a generated blank test image (returns 'no_text_detected'):
    python -m app.modules.image.run_ocr

On first run, PaddleOCR downloads its lightweight recognition/detection weights
(det, rec, cls ~15-20 MB total) into ~/.paddleocr/. Subsequent runs reuse them.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

# Disable oneDNN/MKLDNN on CPU before any paddle imports
os.environ["FLAGS_use_mkldnn"] = "0"
os.environ["FLAGS_use_onednn"] = "0"
os.environ["PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT"] = "0"
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

# Pre-load PyTorch DLLs on Windows before Paddle to prevent WinError 127
try:
    import torch  # noqa: F401
except ImportError:
    pass


def _create_fallback_image() -> str:
    """Create a blank test image and return its path."""
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("Pillow is required. Install via pip install pillow.") from exc

    tmp_dir = Path(tempfile.mkdtemp(prefix="ocr_smoke_"))
    img_path = tmp_dir / "blank_test_image.png"
    img = Image.new("RGB", (256, 128), color=(240, 240, 240))
    img.save(img_path)
    print(f"[info] No --image provided; generated blank test image at {img_path}")
    return str(img_path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run PaddleOCR text extraction (real model, local inference).",
    )
    parser.add_argument(
        "--image",
        type=str,
        default=None,
        help="Path to a local image file. If omitted, a blank test image is generated.",
    )
    args = parser.parse_args()

    # Lazy-import contracts and runner
    from app.modules.image.contracts import OcrInput, OcrStatus
    from app.modules.image.ocr import run

    image_path = args.image or _create_fallback_image()

    print(f"\n{'=' * 60}")
    print(f" PaddleOCR Text Extraction — Smoke Test")
    print(f"{'=' * 60}")
    print(f" Image : {image_path}")
    print(f"{'=' * 60}\n")

    inp = OcrInput(image_path=image_path)
    result = run(inp)

    print(json.dumps(json.loads(result.model_dump_json()), indent=2))

    if result.status == OcrStatus.ERROR:
        print(f"\n[FAIL] OCR Error: {result.error_message}", file=sys.stderr)
        sys.exit(1)
    elif result.status == OcrStatus.NO_TEXT_DETECTED:
        print("\n[OK] Status: NO_TEXT_DETECTED (Clean image without readable text)")
    else:
        print(f"\n[OK] Status: TEXT_DETECTED ({len(result.regions)} region(s) found)")
        print(f"Combined Text:\n{'-' * 40}\n{result.combined_text}\n{'-' * 40}")


if __name__ == "__main__":
    main()

