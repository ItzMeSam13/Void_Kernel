"""
Module 2 — Image Intelligence (Person 3).

Sub-components:
- BLIP image captioning (caption.py)
- CLIP claim-image similarity (similarity.py)
- PaddleOCR text extraction (ocr.py)
- Smaug AI-generated image detection (ai_detect.py)

Public entrypoints:
- analyze_image(image_path, claim_text=None) -> ImageFindings (per-frame video adapter)
- run(input: ImageInput) -> ImageFindings (canonical module entrypoint)
"""

from .analyze_image import analyze_image
from .contracts import ImageFindings, ImageInput
from .run import run

__all__ = ["analyze_image", "run", "ImageInput", "ImageFindings"]

