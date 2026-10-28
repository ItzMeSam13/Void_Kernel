"""
Full end-to-end tests for Module 6 — run.py, Phases 1 + 3 combined.

Two scenarios:
  1. Fully offline (no API keys at all beyond the dummy GOOGLE_API_KEY from
     conftest): claim splitting falls back to a single claim, Tavily/GFC
     return [] (no TAVILY_API_KEY / GOOGLE_FACT_CHECK_API_KEY), evidence
     judge gets no hits -> UNVERIFIABLE. Proves the whole pipeline never
     raises and still produces the real drift_guard score plus Phase-3
     fields, even with zero external evidence (Guiding Principle 4).

  2. Mocked "happy path": Gemini claim-splitter + Gemini evidence judge +
     Tavily search are all mocked to return controlled data, proving the
     Phase-3 wiring (echo-chamber flag -> confidence multiplier, entity
     cross-check against Module 5 metadata) actually connects end to end.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from app.modules.factcheck.contracts import ClaimSource, EvidenceVerdict, FactCheckInput
from app.modules.factcheck.run import run


class TestOfflineFailHonestPipeline:
    """
    Forces the true "every external dependency is down" path, independent
    of whatever is actually in .env (real Tavily/Supabase/Gemini keys may
    well be loaded by the time this runs — see conftest.py). Three things
    are force-disabled regardless of environment:
      - the LLM call itself (claim_splitter.generate patched to raise) —
        unsetting GOOGLE_API_KEY/GEMINI_API_KEY alone no longer does this,
        since FACTCHECK_LLM_BACKEND defaults to local Ollama, which needs
        no key and would otherwise just succeed for real;
      - TAVILY_API_KEY / GOOGLE_FACT_CHECK_API_KEY, so web_search.py still
        exercises its own fail-honest "key not set" path deterministically.
    """

    def test_full_pipeline_completes_without_raising(self, monkeypatch):
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_FACT_CHECK_API_KEY", raising=False)
        with patch(
            "app.modules.factcheck.claim_splitter.generate",
            side_effect=Exception("LLM backend unavailable"),
        ):
            inp = FactCheckInput(
                text="A volcano erupted in Iceland on Monday, displacing hundreds of residents.",
                source=ClaimSource.CAPTION,
            )
            result = run(inp)

        assert result.error is None
        assert len(result.claims) == 1  # LLM unavailable -> single fallback claim
        assert len(result.findings) == 1
        assert result.overall_verdict == EvidenceVerdict.UNVERIFIABLE
        # Drift guard still ran for real (identical text vs. itself -> no drift).
        assert result.drift_detected is False
        assert result.drift_score is not None
        # No search hits at all -> explicitly not flagged (not ambiguous None;
        # that's reserved for zero claims extracted at all).
        assert result.echo_chamber_detected is False
        assert result.unique_source_domains is None
        # NER still ran on the fallback claim.
        assert result.claims[0].location == "Iceland"

    def test_ocr_scene_text_is_accepted_without_raising(self, monkeypatch):
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_FACT_CHECK_API_KEY", raising=False)
        with patch(
            "app.modules.factcheck.claim_splitter.generate",
            side_effect=Exception("LLM backend unavailable"),
        ):
            inp = FactCheckInput(
                text="A fire broke out downtown.",
                source=ClaimSource.OCR,
                ocr_scene_text="Main Street Fire Dept sign visible in background",
            )
            result = run(inp)
        assert result.error is None


class TestMockedHappyPath:
    @patch("app.modules.factcheck.run.google_fact_check_search", return_value=[])
    @patch("app.modules.factcheck.run.adversarial_search_async", new_callable=AsyncMock)
    @patch("app.modules.factcheck.evidence_judge.generate")
    @patch("app.modules.factcheck.claim_splitter.generate")
    def test_echo_chamber_multiplier_applied_through_full_pipeline(
        self, mock_split_generate, mock_judge_generate, mock_search, _mock_gfc
    ):
        # --- claim splitter mock: one claim with a real location/date via NER ---
        mock_split_generate.return_value = (
            '[{"text": "A flood hit Jakarta in 2021.", '
            '"claim_type": "fact", "loaded_language": []}]'
        )

        # --- adversarial search mock: 5 hits all from the same domain (echo chamber) ---
        mock_search.return_value = [
            {"url": f"https://repeat.com/{i}", "title": "t", "snippet": "s", "_source_type": "tavily_confirming"}
            for i in range(5)
        ]

        # --- evidence judge mock: LLM returns a confident SUPPORTED verdict ---
        mock_judge_generate.return_value = (
            '{"evidence": [{"source_url": "https://repeat.com/0", "stance": "supports", "relevance": 0.9}], '
            '"verdict": "supported", "confidence": 0.9, "reasoning": "Matches report."}'
        )

        inp = FactCheckInput(
            text="A flood hit Jakarta in 2021.",
            source=ClaimSource.CAPTION,
            reuse_source_location="Jakarta, Indonesia",
            reuse_source_published_at="2021-05-01T00:00:00Z",
        )
        result = run(inp)

        assert result.error is None
        assert len(result.claims) == 1
        claim = result.claims[0]
        assert claim.location == "Jakarta"

        finding = result.findings[0]
        assert finding.verdict == EvidenceVerdict.SUPPORTED
        # Echo-chamber flagged (single dominant domain) -> 0.9 * 0.75 = 0.675
        assert finding.confidence == 0.675
        assert finding.evidence[0].echo_chamber_flagged is True

        assert result.echo_chamber_detected is True
        assert result.unique_source_domains == 1

        # Entity cross-check against Module 5 metadata: both agree.
        assert finding.entity_signal_agreement["location"]["module5_source"] == "agreed"
        assert finding.entity_signal_agreement["datetime"]["module5_source"] == "agreed"

        assert result.overall_verdict == EvidenceVerdict.SUPPORTED
