"""
Module 2 — Image Intelligence: composition layer.

Invokes the four implemented sub-components (BLIP, CLIP, PaddleOCR, Smaug)
through their established ``run()`` entrypoints and aggregates the results
into a single ``ImageFindings`` object.

Public interface::

    analyze_image(image_path, claim_text=None) -> ImageFindings

This is the function Person 2's video module calls per-frame (via
``stubs.analyze_image_fn``), and the function Module 1's orchestrator will
later call as a LangGraph node.

Design rules (architecture.md §6):
- Each component is invoked independently; a failure in one does not suppress
  results from the others.
- CLIP is skipped (not failed) when no external claim is provided.
- OCR ``no_text_detected`` is a valid success, not an error.
- No overall truth verdict is produced — that belongs to Module 7.
- No LangGraph, FastAPI, or cross-module imports.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from .contracts import (
    BlipCaptionInput,
    BlipCaptionOutput,
    ClipSimilarityInput,
    ClipSimilarityOutput,
    ClipSkippedReason,
    ImageFindings,
    OcrInput,
    OcrOutput,
    OcrStatus,
    ProcessingStatus,
    SmaugDetectionInput,
    SmaugDetectionOutput,
)

logger = logging.getLogger(__name__)


# ── Input validation ─────────────────────────────────────────────────────────

def _validate_image_path(path_str: str) -> Path:
    """Resolve and validate that *path_str* points to an existing file.

    Raises
    ------
    FileNotFoundError
        If the resolved path does not exist.
    IsADirectoryError
        If the resolved path is a directory.
    """
    path = Path(path_str).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Image path does not exist: {path}")
    if path.is_dir():
        raise IsADirectoryError(f"Image path is a directory, not a file: {path}")
    return path


# ── Public entrypoint ────────────────────────────────────────────────────────

def analyze_image(
    image_path: str,
    claim_text: Optional[str] = None,
) -> ImageFindings:
    """Run all applicable image-analysis components on a single image.

    This is the Module 2 composition layer described in architecture.md §2
    (step 4) and team_roadmaps.md Person 3 Phase 1.

    Parameters
    ----------
    image_path : str
        Absolute or relative path to the image file (a standalone image or an
        extracted video frame).
    claim_text : str | None
        An *external* factual claim to compare with the image via CLIP.
        When ``None`` or empty, CLIP is skipped with reason
        ``ClipSkippedReason.NO_CLAIM_PROVIDED``.

    Returns
    -------
    ImageFindings
        Aggregated per-component results.  Each component's field is ``None``
        only when the component was not attempted (currently only CLIP when no
        claim is supplied).  On component failure the field is populated with
        the component's error-status output — other successful components are
        still returned.

    Notes
    -----
    - Components are invoked *sequentially* to avoid loading multiple large
      models in parallel (each singleton caches its model for subsequent calls).
    - OCR text and the BLIP caption are **never** substituted for the caller's
      ``claim_text`` — these are kept separate per architecture.md §1.
    - This function has no dependency on LangGraph, FastAPI, the video module,
      or any other module.
    """
    # ── 0. Validate image path early ─────────────────────────────────────
    try:
        resolved = _validate_image_path(image_path)
    except (FileNotFoundError, IsADirectoryError) as exc:
        # Cannot proceed with any component — return a fully-errored result.
        err_msg = str(exc)
        return ImageFindings(
            image_path=image_path,
            claim_text=claim_text,
            blip=BlipCaptionOutput(
                status=ProcessingStatus.ERROR,
                error_message=err_msg,
            ),
            clip=None,
            clip_skipped_reason=(
                ClipSkippedReason.NO_CLAIM_PROVIDED
                if not (claim_text and claim_text.strip())
                else None
            ),
            smaug=SmaugDetectionOutput(
                status=ProcessingStatus.ERROR,
                error_message=err_msg,
            ),
            ocr=OcrOutput(
                status=OcrStatus.ERROR,
                error_message=err_msg,
            ),
        )

    resolved_str = str(resolved)

    # ── 1. BLIP — image captioning ───────────────────────────────────────
    blip_result: Optional[BlipCaptionOutput] = None
    try:
        from .caption import run as blip_run

        blip_result = blip_run(BlipCaptionInput(image_path=resolved_str))
    except Exception as exc:  # noqa: BLE001
        logger.exception("BLIP component failed")
        blip_result = BlipCaptionOutput(
            status=ProcessingStatus.ERROR,
            error_message=f"BLIP component failed: {exc}",
        )

    # ── 2. CLIP — claim-image similarity (optional) ──────────────────────
    clip_result: Optional[ClipSimilarityOutput] = None
    clip_skipped: Optional[ClipSkippedReason] = None

    if claim_text and claim_text.strip():
        try:
            from .similarity import run as clip_run

            clip_result = clip_run(
                ClipSimilarityInput(
                    image_path=resolved_str,
                    claim_text=claim_text,
                )
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("CLIP component failed")
            clip_result = ClipSimilarityOutput(
                status=ProcessingStatus.ERROR,
                error_message=f"CLIP component failed: {exc}",
            )
    else:
        clip_skipped = ClipSkippedReason.NO_CLAIM_PROVIDED

    # ── 3. PaddleOCR — embedded text extraction ──────────────────────────
    ocr_result: Optional[OcrOutput] = None
    try:
        from .ocr import run as ocr_run

        ocr_result = ocr_run(OcrInput(image_path=resolved_str))
    except Exception as exc:  # noqa: BLE001
        logger.exception("OCR component failed")
        ocr_result = OcrOutput(
            status=OcrStatus.ERROR,
            error_message=f"OCR component failed: {exc}",
        )

    # ── 4. Smaug — AI-generated image detection ─────────────────────────
    smaug_result: Optional[SmaugDetectionOutput] = None
    try:
        from .ai_detect import run as smaug_run

        smaug_result = smaug_run(SmaugDetectionInput(image_path=resolved_str))
    except Exception as exc:  # noqa: BLE001
        logger.exception("Smaug component failed")
        smaug_result = SmaugDetectionOutput(
            status=ProcessingStatus.ERROR,
            error_message=f"Smaug component failed: {exc}",
        )

    # ── 5. Assemble ImageFindings ────────────────────────────────────────
    return ImageFindings(
        image_path=resolved_str,
        claim_text=claim_text,
        blip=blip_result,
        clip=clip_result,
        clip_skipped_reason=clip_skipped,
        smaug=smaug_result,
        ocr=ocr_result,
    )

