"""
Tests for Module 5 — run.py (integration: hashing + mocked DB)

Uses unittest.mock to stub out Supabase calls so the test suite runs
without any DB credentials or network access (architecture §6 rule:
"exercisable with zero orchestration framework installed").
"""
from __future__ import annotations

import io
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from app.modules.reuse.contracts import HammingTier, Modality, ReuseInput
from app.modules.reuse.run import run


def _make_image_bytes(color=(100, 100, 100)) -> bytes:
    img = Image.new("RGB", (64, 64), color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


class TestModuleRunNoDB:
    """run() with DB calls mocked to return empty results — no real Supabase."""

    @patch("app.modules.reuse.run.lookup_by_sha256", return_value=None)
    @patch("app.modules.reuse.run.lookup_by_phash", return_value=[])
    @patch("app.modules.reuse.run.reverse_image_search", return_value=[])
    def test_no_matches_returns_not_reused(self, _rev, _phash, _sha):
        inp = ReuseInput(image_bytes=_make_image_bytes(), modality=Modality.IMAGE)
        result = run(inp)
        assert result.reused is False
        assert result.best_match is None
        assert result.error is None
        assert len(result.query_sha256) == 64

    def test_missing_image_data_returns_error(self):
        inp = ReuseInput()  # neither image_bytes nor image_path
        result = run(inp)
        assert result.error is not None
        assert result.reused is False

    @patch("app.modules.reuse.run.lookup_by_sha256")
    @patch("app.modules.reuse.run.lookup_by_phash", return_value=[])
    @patch("app.modules.reuse.run.reverse_image_search", return_value=[])
    def test_sha256_match_sets_reused_true(self, _rev, _phash, mock_sha):
        from app.modules.reuse.contracts import MatchedSource
        mock_sha.return_value = MatchedSource(
            reference_id="abc-123",
            sha256_match=True,
            phash_hamming=0,
            hamming_tier=HammingTier.SAME,
        )
        inp = ReuseInput(image_bytes=_make_image_bytes(), modality=Modality.IMAGE)
        result = run(inp)
        assert result.reused is True
        assert result.best_match is not None
        assert result.best_match.sha256_match is True

    @patch("app.modules.reuse.run.lookup_by_sha256", side_effect=Exception("DB down"))
    @patch("app.modules.reuse.run.lookup_by_phash", side_effect=Exception("DB down"))
    @patch("app.modules.reuse.run.reverse_image_search", return_value=[])
    def test_db_failure_returns_error_not_raises(self, _rev, _phash, _sha):
        inp = ReuseInput(image_bytes=_make_image_bytes())
        result = run(inp)
        assert result.error is not None
        # Must not raise — Guiding Principle 4
