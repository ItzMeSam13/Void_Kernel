"""
Tests for Module 6 — claim_splitter.py

Mocks out llm_client.generate() so tests run offline without any LLM
backend (Ollama or Gemini). Validates the fallback path (LLM failure)
and happy-path parsing.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from app.modules.factcheck.claim_splitter import split_claims
from app.modules.factcheck.contracts import ClaimType


class TestClaimSplitter:
    def test_empty_text_returns_empty_list(self):
        result = split_claims("   ")
        assert result == []

    @patch("app.modules.factcheck.claim_splitter.generate")
    def test_happy_path_parses_claims(self, mock_generate):
        mock_generate.return_value = '''[
            {"text": "The prime minister resigned.", "claim_type": "fact", "loaded_language": []},
            {"text": "It was a disgraceful retreat.", "claim_type": "framing", "loaded_language": ["disgraceful", "retreat"]}
        ]'''

        claims = split_claims("The prime minister resigned. It was a disgraceful retreat.")
        assert len(claims) == 2
        assert claims[0].claim_type == ClaimType.FACT
        assert claims[1].claim_type == ClaimType.FRAMING
        assert "disgraceful" in claims[1].loaded_language

    @patch("app.modules.factcheck.claim_splitter.generate", side_effect=Exception("LLM error"))
    def test_llm_failure_returns_single_fallback_claim(self, mock_generate):
        claims = split_claims("Some claim text that will fail parsing.")
        # Fallback: return the full text as one FACT claim
        assert len(claims) == 1
        assert claims[0].claim_type == ClaimType.FACT
        assert "Some claim" in claims[0].text

    @patch("app.modules.factcheck.claim_splitter.generate")
    def test_markdown_fence_stripped(self, mock_generate):
        mock_generate.return_value = '```json\n[{"text": "A fact.", "claim_type": "fact", "loaded_language": []}]\n```'

        claims = split_claims("A fact.")
        assert len(claims) == 1
        assert claims[0].text == "A fact."

    @patch("app.modules.factcheck.claim_splitter.generate")
    def test_unknown_claim_type_defaults_to_fact(self, mock_generate):
        mock_generate.return_value = '[{"text": "A claim.", "claim_type": "unknown_type", "loaded_language": []}]'

        claims = split_claims("A claim.")
        assert claims[0].claim_type == ClaimType.FACT
