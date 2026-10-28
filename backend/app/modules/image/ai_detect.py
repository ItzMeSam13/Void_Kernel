"""
Smaug AI-Generated Image Detection — Module 2 sub-component.

Uses ``abacusai/Smaug-AI-Image-Detector`` (439 M-parameter vision-only model,
EmbeddingGemma-2 encoder + linear classification head) to estimate the
probability that an image was AI-generated.

Public entrypoint::

    run(input: SmaugDetectionInput) -> SmaugDetectionOutput

Design decisions (traceable to architecture.md §6 and the task spec):

* **Singleton model lifecycle** — the ``SmaugImageDetect`` detector is loaded
  lazily on the first call via ``snapshot_download`` + ``sys.path`` injection
  (the official loading pattern from the model card) and cached at module level
  for every subsequent call.  Thread-safety is ensured by a ``threading.Lock``.
* **Device selection** — CUDA when available, CPU otherwise.  The model card
  confirms CPU execution is supported (~1 GB memory footprint).
* **File-path interface** — Smaug's official API accepts a file-path string;
  we pass the validated resolved path directly without re-implementing its
  internal preprocessing.
* **Score as-is** — the detector already returns a probability in [0, 1]; no
  sigmoid or softmax is applied on top of the model's own output.
* **Optional label** — a threshold-based label is computed and surfaced as a
  clearly-qualified string ('likely_ai_generated' / 'not_flagged_as_ai_generated').
  The threshold is configurable (default 0.5, from the model card) and exposed
  in the output so consumers know which threshold was used.  The label is
  evidence, not a verdict.
* **Fail honest** — loading failures, invalid images, inference errors, and
  out-of-range scores are reported via ``ProcessingStatus.ERROR`` with a
  human-readable message.  No fabricated scores are ever returned.
* **Independent of CLIP and BLIP** — this module imports nothing from
  ``similarity`` or ``caption``; it shares only the contracts and status enum.

Attribution: Smaug AI Image Detector is © Abacus.AI, released under Apache-2.0.
Model card: https://huggingface.co/abacusai/Smaug-AI-Image-Detector
"""

from __future__ import annotations

import logging
import math
import os
import sys
import threading
from pathlib import Path
from typing import Optional, Tuple

from .contracts import SmaugDetectionInput, SmaugDetectionOutput, ProcessingStatus

logger = logging.getLogger(__name__)

# ── Model configuration ─────────────────────────────────────────────────────

_MODEL_ID: str = "abacusai/Smaug-AI-Image-Detector"

# Honour the existing HF cache env var if set (e.g. inside Docker); otherwise
# fall back to the standard ``~/.cache/huggingface`` location.
_HF_CACHE_DIR: Optional[str] = os.environ.get("HF_HOME") or os.environ.get(
    "TRANSFORMERS_CACHE"
)

# ── Singleton model holder ───────────────────────────────────────────────────

_detector = None          # SmaugImageDetect instance
_model_revision: Optional[str] = None
_lock = threading.Lock()


def _load_detector() -> Tuple[object, Optional[str]]:
    """Download (first time) and load the Smaug detector, caching it.

    Follows the official model-card loading pattern:
    1. ``snapshot_download`` — fetches all repo files to the HF cache dir
       (no re-download on subsequent runs).
    2. ``sys.path.insert`` — makes the repo's ``smaug_image_detect.py``
       importable as a plain Python module.
    3. ``SmaugImageDetect.from_pretrained`` — initialises the model.

    Returns
    -------
    detector, revision
    """
    global _detector, _model_revision  # noqa: PLW0603

    if _detector is not None:
        return _detector, _model_revision

    with _lock:
        if _detector is not None:
            return _detector, _model_revision

        logger.info("Downloading/resolving Smaug model repo '%s' …", _MODEL_ID)

        # Import here so that a missing ``huggingface_hub`` surfaces as a clean
        # error message rather than an ImportError at module-load time.
        try:
            from huggingface_hub import snapshot_download
        except ImportError as exc:
            raise RuntimeError(
                "huggingface_hub is required to load Smaug.  "
                "Ensure it is installed (pip install huggingface_hub)."
            ) from exc

        # snapshot_download respects HF_HOME / TRANSFORMERS_CACHE env vars for
        # the cache location; we pass cache_dir explicitly for clarity.
        repo_path = snapshot_download(
            _MODEL_ID,
            cache_dir=_HF_CACHE_DIR,
        )
        logger.info("Smaug repo resolved at: %s", repo_path)

        # Insert the repo root so ``smaug_image_detect.py`` is importable.
        if repo_path not in sys.path:
            sys.path.insert(0, repo_path)

        try:
            from smaug_image_detect import SmaugImageDetect  # type: ignore[import]
        except ImportError as exc:
            raise RuntimeError(
                f"Could not import SmaugImageDetect from repo at '{repo_path}'. "
                f"The model repo may be incomplete or corrupted: {exc}"
            ) from exc

        logger.info("Loading SmaugImageDetect.from_pretrained('%s') …", _MODEL_ID)
        detector = SmaugImageDetect.from_pretrained(_MODEL_ID)

        # Attempt to extract revision for provenance.
        revision: Optional[str] = None
        try:
            cfg = getattr(detector, "config", None) or getattr(
                getattr(detector, "model", None), "config", None
            )
            if cfg is not None and hasattr(cfg, "_commit_hash"):
                revision = cfg._commit_hash
        except Exception:  # noqa: BLE001
            pass

        _detector, _model_revision = detector, revision
        logger.info("Smaug detector loaded (revision=%s)", revision)
        return _detector, _model_revision


# ── Input validation helpers ─────────────────────────────────────────────────

def _validate_image_path(path_str: str) -> Path:
    """Resolve and validate the image path.

    Raises
    ------
    FileNotFoundError
        If the path does not exist.
    IsADirectoryError
        If the path is a directory.
    """
    path = Path(path_str).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Image path does not exist: {path}")
    if path.is_dir():
        raise IsADirectoryError(f"Image path is a directory, not a file: {path}")
    return path


def _verify_image(path: Path) -> None:
    """Verify the file is a readable image via Pillow.

    Raises
    ------
    PIL.UnidentifiedImageError / OSError / SyntaxError
        If the file cannot be decoded as an image.
    """
    from PIL import Image, UnidentifiedImageError  # lazy import — Docker-only

    img = Image.open(path)
    img.verify()  # raises on corrupt files; leaves the handle in a bad state
    # Re-open just to confirm a full decode succeeds; we discard the result
    # since Smaug's own implementation will open the file by path.
    Image.open(path).convert("RGB").close()


# ── Public entrypoint ────────────────────────────────────────────────────────

def run(input: SmaugDetectionInput) -> SmaugDetectionOutput:
    """Estimate the probability that an image is AI-generated using Smaug.

    This is the module's entire public interface surface (architecture.md §6).
    It can be called directly from a script, unit test, notebook, or — later —
    from the image pipeline's ``analyze_image()`` and the LangGraph orchestrator.

    Parameters
    ----------
    input : SmaugDetectionInput
        Validated image path and optional detection threshold.

    Returns
    -------
    SmaugDetectionOutput
        Structured result with AI-generated probability, optional label,
        model metadata, and status.

    Notes
    -----
    The ``ai_probability`` field is the raw score returned by Smaug — already
    a probability in [0, 1].  Do NOT apply sigmoid or softmax on top of it.
    The optional ``label`` is a threshold-based qualification, not a verdict.
    """
    # ── 1. Validate image path ───────────────────────────────────────────
    try:
        image_path = _validate_image_path(input.image_path)
    except (FileNotFoundError, IsADirectoryError) as exc:
        return SmaugDetectionOutput(
            status=ProcessingStatus.ERROR,
            error_message=str(exc),
        )

    # ── 2. Verify the file is a readable image ───────────────────────────
    try:
        _verify_image(image_path)
    except Exception as exc:  # noqa: BLE001
        return SmaugDetectionOutput(
            status=ProcessingStatus.ERROR,
            error_message=f"Cannot decode image at {image_path}: {exc}",
        )

    # ── 3. Load detector (singleton, first-call lazy init) ───────────────
    try:
        detector, revision = _load_detector()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Smaug detector loading failed")
        return SmaugDetectionOutput(
            status=ProcessingStatus.ERROR,
            error_message=f"Model loading failed: {exc}",
        )

    # ── 4. Run inference ─────────────────────────────────────────────────
    try:
        # Smaug's official API: detector(file_path_string) -> float probability
        raw_score = detector(str(image_path))
        ai_probability: float = float(raw_score)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Smaug inference failed")
        return SmaugDetectionOutput(
            status=ProcessingStatus.ERROR,
            model_revision=revision,
            error_message=f"Inference failed: {exc}",
        )

    # ── 5. Validate score is finite and in [0, 1] ────────────────────────
    if not math.isfinite(ai_probability):
        return SmaugDetectionOutput(
            status=ProcessingStatus.ERROR,
            model_revision=revision,
            error_message=(
                f"Inference produced a non-finite score: {ai_probability}."
            ),
        )
    if not (0.0 <= ai_probability <= 1.0):
        return SmaugDetectionOutput(
            status=ProcessingStatus.ERROR,
            model_revision=revision,
            error_message=(
                f"Inference produced an out-of-range score: {ai_probability}. "
                "Expected a probability in [0.0, 1.0]."
            ),
        )

    # ── 6. Derive optional threshold label ───────────────────────────────
    threshold = input.detection_threshold
    label: str = (
        "likely_ai_generated"
        if ai_probability >= threshold
        else "not_flagged_as_ai_generated"
    )

    # ── 7. Build and return successful output ────────────────────────────
    return SmaugDetectionOutput(
        status=ProcessingStatus.SUCCESS,
        ai_probability=round(ai_probability, 6),
        label=label,
        detection_threshold=threshold,
        model_id=_MODEL_ID,
        model_revision=revision,
    )

