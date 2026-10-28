"""
orchestrator/router_node.py — LangGraph node: input router.

Reads the raw file bytes / content_type already stored in GraphState
and sets `modality` so downstream branch-selection edges can route
to the right modality branch (Module 2 / Module 3 / Module 4 path).

This node is intentionally thin: it does NOT call any model.
All logic lives inside the individual module run() functions.

architecture.md §6 build-sequence step 1:
  "Stand up the thinnest possible LangGraph StateGraph: Module 1's
   router node wired to exactly one modality branch."
"""
from __future__ import annotations

import logging

from app.orchestrator.state import GraphState, InputModality

logger = logging.getLogger(__name__)


# ── MIME-type → modality map ──────────────────────────────────────────────────

_VIDEO_PREFIXES  = ("video/",)
_AUDIO_PREFIXES  = ("audio/",)
_IMAGE_PREFIXES  = ("image/",)

# Plain-text submissions (claim-only, no media file)
_TEXT_ONLY_TYPES = {"text/plain", "application/json"}


def _infer_modality(content_type: str | None) -> InputModality:
    """
    Map a MIME type to one of the three InputModality values.

    Decision table (architecture.md §Module 1):
      video/*        → VIDEO
      audio/*        → AUDIO_ONLY
      image/* or *   → TEXT_IMAGE   (default: image + optional claim text)
    """
    if not content_type:
        return InputModality.TEXT_IMAGE

    ct = content_type.lower().split(";")[0].strip()

    if any(ct.startswith(p) for p in _VIDEO_PREFIXES):
        return InputModality.VIDEO

    if any(ct.startswith(p) for p in _AUDIO_PREFIXES):
        return InputModality.AUDIO_ONLY

    # image/* and text/plain both go through the image+text path
    return InputModality.TEXT_IMAGE


# ── LangGraph node function ───────────────────────────────────────────────────

def router_node(state: GraphState) -> dict:
    """
    LangGraph node: set `modality` in GraphState based on the uploaded file.

    Expected state inputs:
      - `_raw_bytes`   (optional — raw file bytes held in memory during ingestion)
      - `media_path`   (optional — local temp file path)
      - `job_id`       (for logging)

    State outputs:
      - `modality`     InputModality enum value

    The function reads `content_type` from the state if present (set by the
    ARQ task before the graph runs), or falls back to sniffing the file
    extension from `media_path`.
    """
    job_id       = state.get("job_id", "<unknown>")
    content_type = state.get("content_type")   # injected by ARQ task / test harness
    media_path   = state.get("media_path")

    # Fallback: sniff extension when content_type is absent
    if not content_type and media_path:
        content_type = _sniff_from_path(media_path)

    modality = _infer_modality(content_type)

    logger.info(
        "router_node job=%s content_type=%r → modality=%s",
        job_id, content_type, modality.value,
    )

    return {"modality": modality}


def _sniff_from_path(path: str) -> str | None:
    """
    Very lightweight extension-based MIME guess (no python-magic dependency).
    Only used as a fallback when content_type is not injected.
    """
    path = path.lower()
    if path.endswith((".mp4", ".mov", ".webm", ".mkv", ".avi")):
        return "video/mp4"
    if path.endswith((".mp3", ".wav", ".ogg", ".flac", ".m4a")):
        return "audio/mpeg"
    if path.endswith((".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp")):
        return "image/jpeg"
    return None


# ── Edge function for LangGraph conditional routing ───────────────────────────

def route_by_modality(state: GraphState) -> str:
    """
    Conditional edge function: returns the name of the next node to visit
    based on the modality set by router_node.

    Node names must match those registered in pipeline.py.

    Routing plan (architecture.md §2 + §6):
      TEXT_IMAGE  → "image_node"       (Module 2)
      VIDEO       → "video_node"       (Module 3; Module 2 called per-frame internally)
      AUDIO_ONLY  → "audio_node"       (Module 4)
    """
    modality = state.get("modality", InputModality.TEXT_IMAGE)

    if modality == InputModality.VIDEO:
        return "video_node"
    if modality == InputModality.AUDIO_ONLY:
        return "audio_node"
    return "image_node"
