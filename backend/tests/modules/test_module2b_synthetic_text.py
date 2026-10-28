"""
E2E tests for Module 2B — Phase 2 (synthetic-text classifier + length gate).

The length-gate / error paths are pure logic. The classifier path loads
the real `openai-community/roberta-base-openai-detector` pipeline (first
run downloads the model) to prove the wiring genuinely produces a score,
not just that it doesn't crash.
"""
from __future__ import annotations

from unittest.mock import patch

from app.modules.text.contracts import SyntheticTextVerdict, TextInput, TextSource
from app.modules.text.run import run
from app.modules.text.synthetic_text import count_tokens, classify, MIN_TOKEN_COUNT


class TestLengthGate:
    def test_short_text_is_not_assessed(self):
        inp = TextInput(text="too short", source=TextSource.CAPTION)
        result = run(inp)
        assert result.verdict == SyntheticTextVerdict.NOT_ASSESSED
        assert result.score is None
        assert result.method == "not_assessed"
        assert result.error is None

    def test_empty_text_is_not_assessed(self):
        inp = TextInput(text="", source=TextSource.CAPTION)
        result = run(inp)
        assert result.verdict == SyntheticTextVerdict.NOT_ASSESSED
        assert result.text_length == 0

    def test_token_count_is_whitespace_split(self):
        assert count_tokens("one two three") == 3
        assert count_tokens("") == 0


class TestClassifierRealModel:
    """Exercises the real transformers pipeline end to end (network on first call)."""

    LONG_TEXT = (
        "The city council convened on Tuesday to discuss the new transit "
        "proposal. Several residents spoke in favor of expanded bus routes, "
        "while others raised concerns about funding. The vote is expected "
        "next month after a public comment period concludes, officials said."
    )

    def test_classifier_path_returns_score_and_verdict(self):
        assert count_tokens(self.LONG_TEXT) >= MIN_TOKEN_COUNT
        inp = TextInput(text=self.LONG_TEXT, source=TextSource.TRANSCRIPT)
        result = run(inp)

        assert result.method == "classifier"
        assert result.error is None
        assert result.score is not None
        assert 0.0 <= result.score <= 1.0
        assert result.verdict in (
            SyntheticTextVerdict.AI_LIKELY,
            SyntheticTextVerdict.HUMAN_LIKELY,
            SyntheticTextVerdict.INCONCLUSIVE,
        )

    def test_classify_score_consistent_with_verdict(self):
        score, verdict, error = classify(self.LONG_TEXT)
        assert error is None
        if verdict == SyntheticTextVerdict.AI_LIKELY:
            assert score >= 0.65
        elif verdict == SyntheticTextVerdict.HUMAN_LIKELY:
            assert score <= 0.35


class TestClassifierFailure:
    def test_classifier_exception_falls_back_not_assessed(self):
        long_text = "word " * (MIN_TOKEN_COUNT + 5)
        with patch(
            "app.modules.text.synthetic_text._get_classifier",
            side_effect=RuntimeError("model load failed"),
        ):
            inp = TextInput(text=long_text, source=TextSource.OCR)
            result = run(inp)

        assert result.verdict == SyntheticTextVerdict.NOT_ASSESSED
        assert result.score is None
        assert result.error is not None
        assert "model load failed" in result.error
