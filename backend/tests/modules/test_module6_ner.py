"""
E2E tests for Module 6 — Phase 3 NER entity-tagging (claim_splitter.py),
using the real spaCy en_core_web_sm pipeline (no mocking of spaCy itself —
only the Gemini call is mocked/forced to fall back, so split_claims()
exercises its real `_extract_entities` wiring on real text).
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from app.modules.factcheck.claim_splitter import _extract_entities, split_claims


class TestExtractEntitiesDirect:
    def test_location_extracted(self):
        entities = _extract_entities("The earthquake struck Paris yesterday.")
        assert entities["location"] == "Paris"

    def test_date_extracted(self):
        entities = _extract_entities("The meeting happened on March 15, 2021.")
        assert entities["datetime_ref"] is not None
        assert "2021" in entities["datetime_ref"]

    def test_named_people_extracted(self):
        entities = _extract_entities("Barack Obama gave a speech in Chicago.")
        assert "Barack Obama" in entities["named_people"]
        assert entities["location"] == "Chicago"

    def test_empty_text_returns_all_none(self):
        entities = _extract_entities("   ")
        assert entities == {
            "location": None,
            "datetime_ref": None,
            "named_people": [],
            "event_ref": None,
        }

    def test_nlp_failure_fails_open(self):
        with patch(
            "app.modules.factcheck.claim_splitter._get_nlp",
            side_effect=RuntimeError("spaCy model missing"),
        ):
            entities = _extract_entities("Obama spoke in Chicago in 2021.")
        assert entities == {
            "location": None,
            "datetime_ref": None,
            "named_people": [],
            "event_ref": None,
        }


class TestSplitClaimsCarriesEntities:
    def test_fallback_claim_is_tagged_with_entities(self):
        # No GEMINI/GOOGLE key override here beyond the dummy conftest key;
        # force the LLM call itself to fail so we hit the fallback path,
        # which still must run NER on the original text.
        with patch(
            "app.modules.factcheck.claim_splitter.generate",
            side_effect=Exception("LLM down"),
        ):
            claims = split_claims("An earthquake hit Tokyo in March 2021.")

        assert len(claims) == 1
        assert claims[0].location == "Tokyo"
        assert claims[0].datetime_ref is not None
