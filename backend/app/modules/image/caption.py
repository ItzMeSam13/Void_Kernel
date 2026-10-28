"""
BLIP Image Captioning — Module 2 sub-component.

Loads ``Salesforce/blip-image-captioning-base`` once per process and exposes a
single public entrypoint::

    run(input: BlipCaptionInput) -> BlipCaptionOutput

Design decisions (traceable to architecture.md §6 and the task spec):

* **Singleton model lifecycle** — ``BlipForConditionalGeneration`` and
  ``BlipProcessor`` are loaded lazily on first call and reused for every
  subsequent request.  Thread-safety is ensured by a module-level
  ``threading.Lock``.
* **Device selection** — CUDA when available, CPU otherwise.  No GPU is
  *required* to load or run the module.  Consistent with the CLIP component's
  ``_select_device()`` convention.
* **Caption, not verdict** — the generated text is a model-produced description
  of visual content.  It is NOT a truth verdict, confidence score, or
  misinformation label.  BLIP may produce incomplete or incorrect captions.
* **Fail honest** — model-load failures, invalid images, and inference errors
  are reported via ``ProcessingStatus.ERROR`` with a human-readable message.
  No fabricated captions are ever returned.
* **Independent of CLIP** — this component can be loaded, tested, and called
  without importing or running the CLIP similarity component.
"""

from __future__ import annotations

import logging
import os
import threading
from pathlib import Path
from typing import Optional, Tuple

import torch
from PIL import Image, UnidentifiedImageError
from transformers import BlipForConditionalGeneration, BlipProcessor

from .contracts import BlipCaptionInput, BlipCaptionOutput, ProcessingStatus

logger = logging.getLogger(__name__)

# ── Model configuration ─────────────────────────────────────────────────────

_MODEL_ID: str = "Salesforce/blip-image-captioning-base"

# Honour the existing HF cache env var if set (e.g. inside Docker); otherwise
# fall back to the standard ``~/.cache/huggingface`` location.
_HF_CACHE_DIR: Optional[str] = os.environ.get("HF_HOME") or os.environ.get(
    "TRANSFORMERS_CACHE"
)

# ── Singleton model holder ───────────────────────────────────────────────────

_model: Optional[BlipForConditionalGeneration] = None
_processor: Optional[BlipProcessor] = None
_device: Optional[torch.device] = None
_model_revision: Optional[str] = None
_lock = threading.Lock()


def _select_device() -> torch.device:
    """Pick the best available device (GPU if present, else CPU)."""
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def _load_model() -> Tuple[
    BlipForConditionalGeneration, BlipProcessor, torch.device, Optional[str]
]:
    """Load the BLIP model and processor, caching them for the process lifetime.

    Returns
    -------
    model, processor, device, revision
    """
    global _model, _processor, _device, _model_revision  # noqa: PLW0603

    if _model is not None and _processor is not None and _device is not None:
        return _model, _processor, _device, _model_revision

    with _lock:
        # Double-checked locking.
        if _model is not None and _processor is not None and _device is not None:
            return _model, _processor, _device, _model_revision

        logger.info("Loading BLIP model '%s' …", _MODEL_ID)
        device = _select_device()
        logger.info("Selected device: %s", device)

        model = BlipForConditionalGeneration.from_pretrained(
            _MODEL_ID,
            cache_dir=_HF_CACHE_DIR,
        )
        processor = BlipProcessor.from_pretrained(
            _MODEL_ID,
            cache_dir=_HF_CACHE_DIR,
        )
        model = model.to(device)
        model.eval()

        # Try to capture the concrete revision for provenance.
        revision: Optional[str] = None
        try:
            if hasattr(model.config, "_commit_hash"):
                revision = model.config._commit_hash
        except Exception:  # noqa: BLE001
            pass

        _model, _processor, _device, _model_revision = (
            model,
            processor,
            device,
            revision,
        )
        logger.info(
            "BLIP model loaded (device=%s, revision=%s)", device, revision
        )
        return _model, _processor, _device, _model_revision


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


def _open_image(path: Path) -> Image.Image:
    """Open and verify the image via Pillow.

    Raises
    ------
    UnidentifiedImageError / OSError
        If the file cannot be decoded as an image.
    """
    img = Image.open(path)
    img.verify()  # Catch corrupted files early.
    # Re-open because ``verify()`` can leave the file pointer in a bad state.
    img = Image.open(path).convert("RGB")
    return img


# ── Public entrypoint ────────────────────────────────────────────────────────

def run(input: BlipCaptionInput) -> BlipCaptionOutput:
    """Generate a BLIP image caption.

    This is the module's entire public interface surface (architecture.md §6).
    It can be called directly from a script, unit test, notebook, or — later —
    from the image pipeline's ``analyze_image()`` and the LangGraph orchestrator.

    Parameters
    ----------
    input : BlipCaptionInput
        Validated image path.

    Returns
    -------
    BlipCaptionOutput
        Structured result with generated caption, model metadata, and status.
    """
    # ── 1. Validate inputs ───────────────────────────────────────────────
    try:
        image_path = _validate_image_path(input.image_path)
    except (FileNotFoundError, IsADirectoryError) as exc:
        return BlipCaptionOutput(
            status=ProcessingStatus.ERROR,
            error_message=str(exc),
        )

    try:
        image = _open_image(image_path)
    except (UnidentifiedImageError, OSError, SyntaxError) as exc:
        return BlipCaptionOutput(
            status=ProcessingStatus.ERROR,
            error_message=f"Cannot decode image at {image_path}: {exc}",
        )

    # ── 2. Load model (singleton, first-call lazy init) ──────────────────
    try:
        model, processor, device, revision = _load_model()
    except Exception as exc:  # noqa: BLE001
        logger.exception("BLIP model loading failed")
        return BlipCaptionOutput(
            status=ProcessingStatus.ERROR,
            error_message=f"Model loading failed: {exc}",
        )

    # ── 3. Preprocess & generate caption ─────────────────────────────────
    try:
        inputs = processor(
            images=image,
            return_tensors="pt",
        )
        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.no_grad():
            generated_ids = model.generate(
                **inputs,
                max_new_tokens=50,
            )

        # Decode tokens to string, strip special tokens.
        caption: str = processor.decode(
            generated_ids[0],
            skip_special_tokens=True,
        ).strip()

    except Exception as exc:  # noqa: BLE001
        logger.exception("BLIP inference failed")
        return BlipCaptionOutput(
            status=ProcessingStatus.ERROR,
            model_revision=revision,
            error_message=f"Inference failed: {exc}",
        )

    # ── 4. Validate generated caption ────────────────────────────────────
    if not caption:
        return BlipCaptionOutput(
            status=ProcessingStatus.ERROR,
            model_revision=revision,
            error_message="Model generated an empty caption.",
        )

    # ── 5. Build and return successful output ────────────────────────────
    return BlipCaptionOutput(
        status=ProcessingStatus.SUCCESS,
        caption=caption,
        model_id=_MODEL_ID,
        model_revision=revision,
    )
