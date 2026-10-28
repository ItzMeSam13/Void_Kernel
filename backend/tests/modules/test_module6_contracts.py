"""
Tests for Module 6 contracts — ensure schema instantiation works
and all enum values are valid. No network/LLM calls.
"""
from __future__ import annotations

import pytest

from app.modules.factcheck.contracts import (
    AtomicClaim,
    ClaimFindings,
    ClaimSource,
    ClaimType,
    EvidenceItem,
    EvidenceVerdict,
    FactCheckInput,
    SingleClaimFinding,
    Stance,
)


class TestContracts:
    def test_fact_check_input_instantiation(self):
        inp = FactCheckInput(text="The moon is made of cheese.", source=ClaimSource.CAPTION)
        assert inp.text
        assert inp.source == ClaimSource.CAPTION

    def test_atomic_claim_defaults(self):
        c = AtomicClaim(claim_id="c1", text="Test claim.", claim_type=ClaimType.FACT)
        assert c.loaded_language == []
        assert c.location is None

    def test_evidence_item_score_bounds(self):
        with pytest.raises(Exception):
            EvidenceItem(
                source_url="http://x.com",
                snippet="test",
                stance=Stance.SUPPORTS,
                relevance_score=1.5,  # out of bounds
                source_type="web",
            )

    def test_single_claim_finding_has_verdict(self):
        claim = AtomicClaim(claim_id="c1", text="Claim.", claim_type=ClaimType.FACT)
        finding = SingleClaimFinding(
            claim=claim,
            verdict=EvidenceVerdict.UNVERIFIABLE,
            confidence=0.0,
        )
        assert finding.verdict == EvidenceVerdict.UNVERIFIABLE

    def test_claim_findings_aggregate(self):
        claim = AtomicClaim(claim_id="c1", text="Claim.", claim_type=ClaimType.FACT)
        finding = SingleClaimFinding(
            claim=claim,
            verdict=EvidenceVerdict.SUPPORTED,
            confidence=0.8,
        )
        result = ClaimFindings(
            input_text="Claim.",
            source=ClaimSource.CAPTION,
            claims=[claim],
            findings=[finding],
            overall_verdict=EvidenceVerdict.SUPPORTED,
            overall_confidence=0.8,
        )
        assert result.overall_verdict == EvidenceVerdict.SUPPORTED
        assert result.error is None
