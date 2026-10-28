"""
PaddleOCR Text Extraction — Module 2 sub-component.

Extracts text embedded in images (memes, screenshots, news graphics, posters,
video frames, etc.) using PaddleOCR.  Supports both PaddleOCR 2.x and 3.x.

Public entrypoint::

    run(input: OcrInput) -> OcrOutput

Design decisions (traceable to architecture.md §6 and the task spec):

* **Singleton pipeline** — the ``PaddleOCR`` instance is created lazily on the
  first call and reused for every subsequent request.  Thread-safety is ensured
  by a module-level ``threading.Lock``.
* **Version-adaptive API** — PaddleOCR 3.x uses ``.predict()``; 2.x uses
  ``.ocr()``.  The initialisation step detects which is available and selects
  the correct call path.
* **No-text is valid** — an image that contains no text returns
  ``OcrStatus.NO_TEXT_DETECTED`` with an empty ``regions`` list and an empty
  ``combined_text``.  This is NOT an error.
* **Coordinates and confidence preserved** — each detected region retains its
  bounding-box polygon and per-region recognition confidence.  Low-confidence
  detections are included; downstream consumers decide what to filter.
* **Fail honest** — initialisation failures, invalid images, and inference
  errors produce ``OcrStatus.ERROR`` with a human-readable message.  No
  fabricated text is ever returned.
* **Independent of CLIP, BLIP, Smaug** — this module has no imports from the
  other image sub-components.  It shares only the contracts.
* **OCR text is evidence, not fact** — the ``combined_text`` field is provided
  for downstream use (e.g. Module 6 fact-checking).  This component does NOT
  query Tavily, assert claim truth, or forward text to any external service.
"""

from __future__ import annotations

import logging
import os
import threading
from pathlib import Path
from typing import List, Optional, Tuple

# Disable oneDNN/MKLDNN on CPU to bypass PaddlePaddle 3.x PIR executor bug on Windows
# ("ConvertPirAttribute2RuntimeAttribute not support pir::ArrayAttribute")
os.environ["FLAGS_use_mkldnn"] = "0"
os.environ["FLAGS_use_onednn"] = "0"
os.environ["PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT"] = "0"
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

from .contracts import OcrInput, OcrOutput, OcrStatus, OcrTextRegion

logger = logging.getLogger(__name__)

# ── Singleton pipeline holder ────────────────────────────────────────────────

_ocr_pipeline = None      # PaddleOCR instance
_ocr_api_version: Optional[str] = None   # "2x" | "3x"
_lock = threading.Lock()


def _load_pipeline() -> Tuple[object, str]:
    """Initialise the PaddleOCR pipeline once per process.

    Detects whether PaddleOCR 3.x (`.predict()` API) or 2.x (`.ocr()` API)
    is installed and stores which call path to use.

    Returns
    -------
    pipeline, api_version  ("3x" or "2x")

    Raises
    ------
    RuntimeError
        If PaddleOCR cannot be imported or initialised.
    """
    global _ocr_pipeline, _ocr_api_version  # noqa: PLW0603

    if _ocr_pipeline is not None and _ocr_api_version is not None:
        return _ocr_pipeline, _ocr_api_version

    with _lock:
        if _ocr_pipeline is not None and _ocr_api_version is not None:
            return _ocr_pipeline, _ocr_api_version

        # On Windows, PyTorch's C++ DLLs must be loaded before Paddle's DLLs
        # into the process memory to prevent WinError 127 (shm.dll symbol collision).
        try:
            import torch  # noqa: F401
        except ImportError:
            pass

        try:
            import paddle
            paddle.set_flags({
                "FLAGS_use_mkldnn": False,
                "FLAGS_use_onednn": False,
            })
        except Exception:
            pass

        try:
            from paddleocr import PaddleOCR  # type: ignore[import]
        except ImportError as exc:
            raise RuntimeError(
                "paddleocr is required but could not be imported.  "
                "Ensure paddleocr and paddlepaddle are installed."
            ) from exc

        logger.info("Initialising PaddleOCR pipeline …")

        # Use ordinary text detection and recognition. Disable document layout / unwarping
        # (UVDoc) per architecture.md §1 & §2, and use stable PP-OCRv4.
        try:
            pipeline = PaddleOCR(
                lang="en",
                ocr_version="PP-OCRv4",
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
            )
        except (ValueError, TypeError):
            try:
                pipeline = PaddleOCR(lang="en")
            except (ValueError, TypeError):
                # Fallback for legacy PaddleOCR 2.x
                pipeline = PaddleOCR(
                    lang="en",
                    use_angle_cls=False,
                    show_log=False,
                )

        # Detect API version: 3.x exposes `.predict()`; 2.x uses `.ocr()`.
        if hasattr(pipeline, "predict") and callable(pipeline.predict):
            api_version = "3x"
        else:
            api_version = "2x"

        _ocr_pipeline, _ocr_api_version = pipeline, api_version
        logger.info("PaddleOCR pipeline ready (api_version=%s)", api_version)
        return _ocr_pipeline, _ocr_api_version


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
    from PIL import Image, UnidentifiedImageError  # lazy import — Docker only

    img = Image.open(path)
    img.verify()


# ── Result normalisation ─────────────────────────────────────────────────────

def _parse_result_3x(raw_results: list) -> List[OcrTextRegion]:
    """Normalise PaddleOCR 3.x ``.predict()`` output.

    PaddleX OCRResult objects support dict access or `.json` property, with
    keys ``rec_texts``, ``rec_scores``, and ``rec_polys`` / ``dt_polys``.
    """
    regions: List[OcrTextRegion] = []
    for res in raw_results:
        try:
            data = None
            if hasattr(res, "json"):
                data = res.json() if callable(res.json) else res.json
            elif isinstance(res, dict):
                data = res

            # Unwrap nested {"res": {...}} if present.
            if isinstance(data, dict) and "res" in data:
                data = data["res"]

            # If not a dict or empty, fallback to direct attribute / item lookup on res
            if not isinstance(data, dict):
                data = {}

            def _get_val(keys: list):
                for k in keys:
                    if k in data:
                        return data[k]
                    if hasattr(res, k):
                        return getattr(res, k)
                    try:
                        if hasattr(res, "__getitem__") and k in res:
                            return res[k]
                    except Exception:
                        pass
                return []

            texts = _get_val(["rec_texts", "rec_text"])
            scores = _get_val(["rec_scores", "rec_score"])
            polys = _get_val(["rec_polys", "dt_polys", "rec_boxes"])

            # Convert numpy arrays to standard lists
            if hasattr(texts, "tolist"):
                texts = texts.tolist()
            if hasattr(scores, "tolist"):
                scores = scores.tolist()
            if hasattr(polys, "tolist"):
                polys = polys.tolist()

            for i, text in enumerate(texts):
                text_str = str(text).strip()
                if not text_str:
                    continue
                confidence: Optional[float] = None
                if i < len(scores):
                    try:
                        confidence = round(float(scores[i]), 4)
                    except (TypeError, ValueError):
                        pass
                bbox: Optional[List[List[float]]] = None
                if i < len(polys):
                    try:
                        raw_poly = polys[i]
                        if hasattr(raw_poly, "tolist"):
                            raw_poly = raw_poly.tolist()
                        bbox = [[round(float(c), 2) for c in pt] for pt in raw_poly]
                    except (TypeError, ValueError):
                        pass
                regions.append(OcrTextRegion(
                    text=text_str,
                    confidence=confidence,
                    bounding_box=bbox,
                ))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not parse a 3.x OCR result element: %s", exc)
    return regions


def _parse_result_2x(raw_results: list) -> List[OcrTextRegion]:
    """Normalise PaddleOCR 2.x ``.ocr()`` output.

    The 2.x API returns a list (one per image).  Each element is a list of
    detections; each detection is ``[bounding_box, (text, confidence)]``.
    """
    regions: List[OcrTextRegion] = []
    # 2.x wraps in an outer list for batched inputs; unwrap one level.
    if raw_results and isinstance(raw_results[0], list):
        detections = raw_results[0]
    else:
        detections = raw_results

    if not detections:
        return regions

    for detection in detections:
        try:
            if detection is None:
                continue
            if len(detection) != 2:
                continue
            box_raw, rec = detection
            text_str = str(rec[0]).strip() if rec else ""
            if not text_str:
                continue
            confidence: Optional[float] = None
            if rec and len(rec) > 1:
                try:
                    confidence = float(rec[1])
                except (TypeError, ValueError):
                    pass
            bbox: Optional[List[List[float]]] = None
            if box_raw:
                try:
                    bbox = [[float(c) for c in pt] for pt in box_raw]
                except (TypeError, ValueError):
                    pass
            regions.append(OcrTextRegion(
                text=text_str,
                confidence=confidence,
                bounding_box=bbox,
            ))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not parse a 2.x OCR detection: %s", exc)
    return regions


# ── Public entrypoint ────────────────────────────────────────────────────────

def run(input: OcrInput) -> OcrOutput:
    """Extract text from an image using PaddleOCR.

    This is the module's entire public interface surface (architecture.md §6).
    It can be called directly from a script, unit test, notebook, or — later —
    from ``analyze_image()`` and the LangGraph orchestrator.

    Parameters
    ----------
    input : OcrInput
        Validated image path.

    Returns
    -------
    OcrOutput
        Structured result with detected regions, combined text, and status.
        An image with no text returns ``OcrStatus.NO_TEXT_DETECTED`` — this
        is a valid successful outcome, not an error.

    Notes
    -----
    ``combined_text`` is raw extracted text suitable as evidence for downstream
    fact-checking (Module 6).  It is NOT a substitute for the caller's supplied
    claim, and this component does NOT verify its truthfulness.
    """
    # ── 1. Validate image path ───────────────────────────────────────────
    try:
        image_path = _validate_image_path(input.image_path)
    except (FileNotFoundError, IsADirectoryError) as exc:
        return OcrOutput(
            status=OcrStatus.ERROR,
            error_message=str(exc),
        )

    # ── 2. Verify the file is a readable image ───────────────────────────
    try:
        _verify_image(image_path)
    except Exception as exc:  # noqa: BLE001
        return OcrOutput(
            status=OcrStatus.ERROR,
            error_message=f"Cannot decode image at {image_path}: {exc}",
        )

    # ── 3. Load pipeline (singleton, first-call lazy init) ───────────────
    try:
        pipeline, api_version = _load_pipeline()
    except Exception as exc:  # noqa: BLE001
        logger.exception("PaddleOCR pipeline initialisation failed")
        return OcrOutput(
            status=OcrStatus.ERROR,
            error_message=f"OCR engine initialisation failed: {exc}",
        )

    # ── 4. Run inference ─────────────────────────────────────────────────
    try:
        path_str = str(image_path)
        if api_version == "3x":
            raw = list(pipeline.predict(path_str))
            regions = _parse_result_3x(raw)
        else:
            raw = pipeline.ocr(path_str, cls=False)
            regions = _parse_result_2x(raw if raw is not None else [])
    except Exception as exc:  # noqa: BLE001
        logger.exception("PaddleOCR inference failed")
        return OcrOutput(
            status=OcrStatus.ERROR,
            error_message=f"OCR inference failed: {exc}",
        )

    # ── 5. Build output ──────────────────────────────────────────────────
    if not regions:
        return OcrOutput(
            status=OcrStatus.NO_TEXT_DETECTED,
            regions=[],
            combined_text="",
        )

    combined_text = "\n".join(r.text for r in regions)
    return OcrOutput(
        status=OcrStatus.TEXT_DETECTED,
        regions=regions,
        combined_text=combined_text,
    )

