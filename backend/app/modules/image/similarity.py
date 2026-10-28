"""
CLIP Claim-Image Similarity — Module 2 sub-component.

Loads ``openai/clip-vit-base-patch32`` once per process and exposes a single
public entrypoint::

    run(input: ClipSimilarityInput) -> ClipSimilarityOutput

Design decisions (traceable to architecture.md §6 and the task spec):

* **Singleton model lifecycle** — ``CLIPModel`` and ``CLIPProcessor`` are loaded
  lazily on first call and reused for every subsequent request.  Thread-safety
  is ensured by a module-level ``threading.Lock``.
* **Device selection** — CUDA when available, CPU otherwise.  No GPU is
  *required* to load or run the module.
* **Cosine similarity** is the primary metric (normalised image/text
  embeddings, dot product).  The model's raw ``logits_per_image`` is also
  returned, clearly separated, so downstream consumers can choose.
* **No interpretation** — the score is NOT labelled as "fake" or "real", and no
  hard-coded thresholds are applied.  Interpretation is the fusion layer's job
  (Module 7).
* **Fail honest** — model-load failures, invalid images, and inference errors
  are reported via ``ProcessingStatus.ERROR`` with a human-readable message.
  No fabricated scores are ever returned.
"""

from __future__ import annotations

import logging
import math
import os
import threading
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import torch
from PIL import Image, UnidentifiedImageError
from transformers import CLIPModel, CLIPProcessor

from .contracts import ClipSimilarityInput, ClipSimilarityOutput, ProcessingStatus

logger = logging.getLogger(__name__)

# ── Model configuration ─────────────────────────────────────────────────────

_MODEL_ID: str = "openai/clip-vit-base-patch32"

# Honour the existing HF cache env var if set (e.g. inside Docker); otherwise
# fall back to the standard ``~/.cache/huggingface`` location.
_HF_CACHE_DIR: Optional[str] = os.environ.get("HF_HOME") or os.environ.get(
    "TRANSFORMERS_CACHE"
)

# ── Singleton model holder ───────────────────────────────────────────────────

_model: Optional[CLIPModel] = None
_processor: Optional[CLIPProcessor] = None
_device: Optional[torch.device] = None
_model_revision: Optional[str] = None
_lock = threading.Lock()


def _select_device() -> torch.device:
    """Pick the best available device (GPU if present, else CPU)."""
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def _load_model() -> Tuple[CLIPModel, CLIPProcessor, torch.device, Optional[str]]:
    """Load the CLIP model and processor, caching them for the process lifetime.

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

        logger.info("Loading CLIP model '%s' …", _MODEL_ID)
        device = _select_device()
        logger.info("Selected device: %s", device)

        model = CLIPModel.from_pretrained(
            _MODEL_ID,
            cache_dir=_HF_CACHE_DIR,
        )
        processor = CLIPProcessor.from_pretrained(
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
            "CLIP model loaded (device=%s, revision=%s)", device, revision
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


def _validate_claim_text(text: str) -> str:
    """Ensure the claim text is non-empty after stripping whitespace.

    Raises
    ------
    ValueError
        If the text is empty or whitespace-only.
    """
    stripped = text.strip()
    if not stripped:
        raise ValueError("Claim text must be non-empty (received whitespace-only string).")
    return stripped


# ── Public entrypoint ────────────────────────────────────────────────────────

def run(input: ClipSimilarityInput) -> ClipSimilarityOutput:
    """Compute CLIP claim-image similarity.

    This is the module's entire public interface surface (architecture.md §6).
    It can be called directly from a script, unit test, notebook, or — later —
    from the image pipeline's ``analyze_image()`` and the LangGraph orchestrator.

    Parameters
    ----------
    input : ClipSimilarityInput
        Validated image path and claim text.

    Returns
    -------
    ClipSimilarityOutput
        Structured result with similarity score, model metadata, and status.
    """
    # ── 1. Validate inputs ───────────────────────────────────────────────
    try:
        image_path = _validate_image_path(input.image_path)
    except (FileNotFoundError, IsADirectoryError) as exc:
        return ClipSimilarityOutput(
            status=ProcessingStatus.ERROR,
            error_message=str(exc),
        )

    try:
        claim_text = _validate_claim_text(input.claim_text)
    except ValueError as exc:
        return ClipSimilarityOutput(
            status=ProcessingStatus.ERROR,
            error_message=str(exc),
        )

    try:
        image = _open_image(image_path)
    except (UnidentifiedImageError, OSError, SyntaxError) as exc:
        return ClipSimilarityOutput(
            status=ProcessingStatus.ERROR,
            error_message=f"Cannot decode image at {image_path}: {exc}",
        )

    # ── 2. Load model (singleton, first-call lazy init) ──────────────────
    try:
        model, processor, device, revision = _load_model()
    except Exception as exc:  # noqa: BLE001
        logger.exception("CLIP model loading failed")
        return ClipSimilarityOutput(
            status=ProcessingStatus.ERROR,
            error_message=f"Model loading failed: {exc}",
        )

    # ── 3. Preprocess & run inference ────────────────────────────────────
    try:
        inputs = processor(
            text=[claim_text],
            images=image,
            return_tensors="pt",
            padding=True,
            truncation=True,
        )
        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = model(**inputs)

        # Raw logits — shape (1, 1).
        logits_per_image: float = outputs.logits_per_image[0, 0].item()

        # Normalised cosine similarity from the embeddings directly.
        image_embeds = outputs.image_embeds  # (1, D)
        text_embeds = outputs.text_embeds    # (1, D)

        # L2-normalise (CLIP already normalises internally, but be explicit).
        image_embeds = image_embeds / image_embeds.norm(dim=-1, keepdim=True)
        text_embeds = text_embeds / text_embeds.norm(dim=-1, keepdim=True)

        cosine_sim: float = (image_embeds @ text_embeds.T)[0, 0].item()

    except Exception as exc:  # noqa: BLE001
        logger.exception("CLIP inference failed")
        return ClipSimilarityOutput(
            status=ProcessingStatus.ERROR,
            model_revision=revision,
            error_message=f"Inference failed: {exc}",
        )

    # ── 4. Sanity-check: finite numbers only ─────────────────────────────
    if not math.isfinite(cosine_sim) or not math.isfinite(logits_per_image):
        return ClipSimilarityOutput(
            status=ProcessingStatus.ERROR,
            model_revision=revision,
            error_message=(
                "Inference produced non-finite values "
                f"(cosine_sim={cosine_sim}, logits={logits_per_image})."
            ),
        )

    # ── 5. Build and return successful output ────────────────────────────
    limitations: Optional[str] = None
    if len(claim_text.split()) < 3:
        limitations = (
            "Very short claim text (< 3 words); CLIP similarity may be less "
            "meaningful for extremely short phrases."
        )

    return ClipSimilarityOutput(
        status=ProcessingStatus.SUCCESS,
        similarity_score=round(cosine_sim, 6),
        logits_per_image=round(logits_per_image, 4),
        comparison_method="cosine_similarity",
        model_id=_MODEL_ID,
        model_revision=revision,
        limitations=limitations,
    )
