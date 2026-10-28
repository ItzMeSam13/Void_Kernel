"""
modules/reuse/hashing.py — SHA-256 + pHash utilities (Module 5).

Reuses the same fingerprinting logic as document_forgery's ingestion module:
  - SHA-256: exact-match identification
  - pHash (DCT-based perceptual hash): visual similarity with Hamming-distance tiers
      < 5  → "same"
      5–15 → "modified"
      > 15 → "different"

These utilities have zero dependency on orchestration or other modules.
Callable standalone for any image or video keyframe bytes.
"""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Hamming-distance tier thresholds (architecture.md §Module 5)
SAME_THRESHOLD     = 5
MODIFIED_THRESHOLD = 15


def compute_sha256(data: bytes) -> str:
    """Return the lowercase hex SHA-256 digest of *data*."""
    return hashlib.sha256(data).hexdigest()


def compute_phash(image_bytes: bytes) -> Optional[str]:
    """
    Compute a DCT-based perceptual hash of an image.
    Returns the hex string representation, or None if the bytes are not
    a valid image or imagehash is not installed.
    """
    try:
        import imagehash
        from PIL import Image
        import io

        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        phash = imagehash.phash(img)
        return str(phash)          # hex string, e.g. "f8e0c8a0d090e8f0"
    except ImportError:
        logger.warning("imagehash or Pillow not installed — pHash unavailable.")
        return None
    except Exception as exc:       # noqa: BLE001
        logger.debug("compute_phash failed: %s", exc)
        return None


def compute_phash_from_path(path: str | Path) -> Optional[str]:
    """Convenience wrapper: read file from *path* then compute pHash."""
    try:
        return compute_phash(Path(path).read_bytes())
    except OSError as exc:
        logger.debug("compute_phash_from_path(%s) read error: %s", path, exc)
        return None


def hamming_distance(hex_a: str, hex_b: str) -> Optional[int]:
    """
    Compute Hamming distance between two pHash hex strings.
    Returns None if either hash is invalid or imagehash is not installed.
    """
    try:
        import imagehash
        ha = imagehash.hex_to_hash(hex_a)
        hb = imagehash.hex_to_hash(hex_b)
        return ha - hb
    except Exception as exc:       # noqa: BLE001
        logger.debug("hamming_distance failed: %s", exc)
        return None


def phash_tier(distance: int) -> str:
    """
    Map a Hamming distance to a reuse tier string.
    Tiers match architecture.md §Module 5 / ml_exisitng_assets.md.
    """
    if distance < SAME_THRESHOLD:
        return "same"
    if distance <= MODIFIED_THRESHOLD:
        return "modified"
    return "different"


def read_bytes(media_path: str | Path) -> bytes:
    """Read a file to bytes; raises OSError on failure."""
    return Path(media_path).read_bytes()
