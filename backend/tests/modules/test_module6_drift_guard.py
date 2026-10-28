"""
E2E tests for Module 6 — Phase 3 drift_guard.py (real sentence-transformers
cosine-similarity check, replacing the Phase-1 always-False stub).
"""
from __future__ import annotations

from unittest.mock import patch

from app.modules.factcheck.drift_guard import check_drift, DRIFT_THRESHOLD


class TestDriftGuardRealModel:
    def test_identical_text_has_no_drift(self):
        text = "The prime minister resigned on Monday after the vote."
        drift_detected, drift_score = check_drift(text, [text])
        assert drift_detected is False
        assert drift_score is not None
        assert drift_score < DRIFT_THRESHOLD

    def test_semantically_similar_claims_have_low_drift(self):
        original = "The city council approved the new transit budget on Tuesday."
        recomposed = ["The council passed the transit budget this week."]
        drift_detected, drift_score = check_drift(original, recomposed)
        assert drift_score is not None
        assert drift_detected is False

    def test_unrelated_text_flags_drift(self):
        original = "The city council approved the new transit budget on Tuesday."
        recomposed = ["A giant panda was born at the zoo over the weekend."]
        drift_detected, drift_score = check_drift(original, recomposed)
        assert drift_score is not None
        assert drift_detected is True
        assert drift_score > DRIFT_THRESHOLD


class TestDriftGuardEdgeCases:
    def test_empty_original_text_skips_check(self):
        drift_detected, drift_score = check_drift("", ["some claim"])
        assert drift_detected is False
        assert drift_score is None

    def test_empty_claims_skips_check(self):
        drift_detected, drift_score = check_drift("some text", [])
        assert drift_detected is False
        assert drift_score is None

    def test_model_failure_fails_open(self):
        with patch(
            "app.modules.factcheck.drift_guard._get_model",
            side_effect=RuntimeError("model unavailable"),
        ):
            drift_detected, drift_score = check_drift("original text here", ["recomposed claim"])
        assert drift_detected is False
        assert drift_score is None
