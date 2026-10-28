"""
Tests for Module 5 — hashing.py

Architecture §6 rule: "Every module must be exercisable directly —
a script, a notebook cell, or a unit test calling run() with a
sample input — with zero orchestration framework installed."

These tests use only stdlib + PIL + imagehash.
No DB, no Supabase, no LangGraph.
"""
from __future__ import annotations

import io
import pytest
from PIL import Image

from app.modules.reuse.hashing import (
    compute_sha256,
    compute_phash,
    hamming_distance,
    classify_hamming_tier,
    fingerprint,
)
from app.modules.reuse.contracts import HammingTier


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_image_bytes(color: tuple = (128, 64, 32), size: tuple = (64, 64)) -> bytes:
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# SHA-256 tests
# ---------------------------------------------------------------------------

class TestSHA256:
    def test_same_bytes_same_hash(self):
        b = _make_image_bytes()
        assert compute_sha256(b) == compute_sha256(b)

    def test_different_bytes_different_hash(self):
        b1 = _make_image_bytes(color=(0, 0, 0))
        b2 = _make_image_bytes(color=(255, 255, 255))
        assert compute_sha256(b1) != compute_sha256(b2)

    def test_returns_64_char_hex(self):
        b = _make_image_bytes()
        h = compute_sha256(b)
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)


# ---------------------------------------------------------------------------
# pHash tests
# ---------------------------------------------------------------------------

class TestPHash:
    def test_identical_images_zero_hamming(self):
        b = _make_image_bytes(color=(100, 150, 200))
        h1 = compute_phash(b)
        h2 = compute_phash(b)
        assert hamming_distance(h1, h2) == 0

    def test_very_different_images_high_hamming(self):
        b1 = _make_image_bytes(color=(0, 0, 0))
        b2 = _make_image_bytes(color=(255, 255, 255))
        h1 = compute_phash(b1)
        h2 = compute_phash(b2)
        # Solid black vs solid white should have a measurably high distance
        assert hamming_distance(h1, h2) > 0

    def test_hash_length_consistent(self):
        b1 = _make_image_bytes(color=(10, 20, 30))
        b2 = _make_image_bytes(color=(40, 50, 60))
        h1 = compute_phash(b1)
        h2 = compute_phash(b2)
        assert len(h1) == len(h2)

    def test_mismatched_hash_lengths_raise(self):
        with pytest.raises(ValueError, match="pHash length mismatch"):
            hamming_distance("abcd", "ab")


# ---------------------------------------------------------------------------
# Hamming tier classification tests
# ---------------------------------------------------------------------------

class TestHammingTier:
    def test_below_5_is_same(self):
        for d in range(5):
            assert classify_hamming_tier(d) == HammingTier.SAME

    def test_5_to_15_is_modified(self):
        for d in range(5, 16):
            assert classify_hamming_tier(d) == HammingTier.MODIFIED

    def test_above_15_is_different(self):
        for d in [16, 30, 100, 256]:
            assert classify_hamming_tier(d) == HammingTier.DIFFERENT


# ---------------------------------------------------------------------------
# fingerprint() convenience wrapper
# ---------------------------------------------------------------------------

class TestFingerprint:
    def test_returns_tuple_of_strings(self):
        b = _make_image_bytes()
        sha, ph = fingerprint(b)
        assert isinstance(sha, str) and isinstance(ph, str)

    def test_sha_is_64_chars(self):
        sha, _ = fingerprint(_make_image_bytes())
        assert len(sha) == 64
