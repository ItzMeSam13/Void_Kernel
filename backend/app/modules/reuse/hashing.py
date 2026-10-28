"""
<<<<<<< HEAD
Module 5 — hashing.py
SHA-256 + perceptual-hash (pHash) fingerprinting.

Ported from document_forgery's ingestion/blockchain module
(architecture.md §Asset Reuse Matrix: "Reuse as-is").
Hamming-distance tier logic mirrors document_forgery exactly:
  < 5   → SAME
  5–15  → MODIFIED
  > 15  → DIFFERENT

This file is pure-function: no I/O, no DB calls, no side effects.
=======
modules/reuse/hashing.py — SHA-256 + pHash utilities (Module 5).

Reuses the same fingerprinting logic as document_forgery's ingestion module:
  - SHA-256: exact-match identification
  - pHash (DCT-based perceptual hash): visual similarity with Hamming-distance tiers
      < 5  → "same"
      5–15 → "modified"
      > 15 → "different"

These utilities have zero dependency on orchestration or other modules.
Callable standalone for any image or video keyframe bytes.
>>>>>>> d3d2c45df93abffce0459e62fed0f32a1920cf8f
"""
from __future__ import annotations

import hashlib
<<<<<<< HEAD
import io
from typing import Union

import imagehash
from PIL import Image

from .contracts import HammingTier


# ---------------------------------------------------------------------------
# Constants — ported from document_forgery's provenance layer
# ---------------------------------------------------------------------------
HAMMING_SAME_THRESHOLD = 5      # < 5
HAMMING_MODIFIED_THRESHOLD = 15  # 5–15


def _load_pil(image_data: Union[bytes, str]) -> Image.Image:
    """Load a PIL Image from raw bytes or a file path."""
    if isinstance(image_data, bytes):
        return Image.open(io.BytesIO(image_data)).convert("RGB")
    return Image.open(image_data).convert("RGB")


def compute_sha256(image_data: Union[bytes, str]) -> str:
    """
    Return the hex SHA-256 digest of the raw image bytes.

    If `image_data` is a file path, the file is read in binary mode.
    The digest is computed over the raw bytes (not the decoded pixel array)
    so it is stable across PIL version changes.
    """
    if isinstance(image_data, str):
        with open(image_data, "rb") as fh:
            raw = fh.read()
    else:
        raw = image_data
    return hashlib.sha256(raw).hexdigest()


def compute_phash(image_data: Union[bytes, str], hash_size: int = 16) -> str:
    """
    Return the perceptual hash (pHash) of the image as a hex string.

    hash_size=16 → 256-bit pHash, giving Hamming distances in [0, 256].
    The default in imagehash is 8 (64-bit); 16 is used here to reduce
    false positives on visually-similar-but-different images.
    """
    img = _load_pil(image_data)
    return str(imagehash.phash(img, hash_size=hash_size))


def hamming_distance(hash_a: str, hash_b: str) -> int:
    """
    Compute the Hamming distance between two pHash hex strings.
    Raises ValueError if the hashes have different lengths.
    """
    if len(hash_a) != len(hash_b):
        raise ValueError(
            f"pHash length mismatch: {len(hash_a)} vs {len(hash_b)}. "
            "Ensure both hashes were computed with the same hash_size."
        )
    # imagehash hex strings encode bits directly; XOR over parsed integers
    a_int = int(hash_a, 16)
    b_int = int(hash_b, 16)
    return bin(a_int ^ b_int).count("1")


def classify_hamming_tier(distance: int) -> HammingTier:
    """
    Map a raw Hamming distance to a HammingTier enum value.
    Thresholds are ported from document_forgery verbatim.
    """
    if distance < HAMMING_SAME_THRESHOLD:
        return HammingTier.SAME
    if distance <= HAMMING_MODIFIED_THRESHOLD:
        return HammingTier.MODIFIED
    return HammingTier.DIFFERENT


def fingerprint(image_data: Union[bytes, str]) -> tuple[str, str]:
    """
    Convenience wrapper: return (sha256_hex, phash_hex) in one call.
    Used by reference_store.py and the lookup path in run().
    """
    sha = compute_sha256(image_data)
    ph = compute_phash(image_data)
    return sha, ph
=======
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
>>>>>>> d3d2c45df93abffce0459e62fed0f32a1920cf8f
