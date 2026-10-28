"""
Module 5 — hashing.py
SHA-256 + perceptual-hash (pHash) fingerprinting.

Ported from document_forgery's ingestion/blockchain module
(architecture.md §Asset Reuse Matrix: "Reuse as-is").
Hamming-distance tier logic mirrors document_forgery exactly:
  < 5   → SAME
  5–15  → MODIFIED
  > 15  → DIFFERENT

This file is pure-function: no I/O, no DB calls, no side effects.
"""
from __future__ import annotations

import hashlib
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
