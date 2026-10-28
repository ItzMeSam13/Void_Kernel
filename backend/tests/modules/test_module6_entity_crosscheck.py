"""
E2E tests for Module 6 — Phase 3 entity x signal agreement matrix
(entity_crosscheck.py), cross-checking claim NER entities against
Module 5's widened source metadata.
"""
from __future__ import annotations

from app.modules.factcheck.contracts import AtomicClaim, ClaimType
from app.modules.factcheck.entity_crosscheck import (
    AGREED,
    DISAGREED,
    UNVERIFIABLE,
    build_entity_signal_agreement,
)


def _claim(**kwargs) -> AtomicClaim:
    defaults = dict(claim_id="c1", text="A claim.", claim_type=ClaimType.FACT)
    defaults.update(kwargs)
    return AtomicClaim(**defaults)


class TestNoEntities:
    def test_no_entities_returns_none(self):
        claim = _claim()
        matrix = build_entity_signal_agreement(claim)
        assert matrix is None


class TestLocationAgreement:
    def test_location_agrees_with_source(self):
        claim = _claim(location="Paris")
        matrix = build_entity_signal_agreement(claim, reuse_source_location="Paris, France")
        assert matrix["location"]["module5_source"] == AGREED

    def test_location_disagrees_with_source(self):
        claim = _claim(location="Paris")
        matrix = build_entity_signal_agreement(claim, reuse_source_location="Tokyo, Japan")
        assert matrix["location"]["module5_source"] == DISAGREED

    def test_location_unverifiable_without_source(self):
        claim = _claim(location="Paris")
        matrix = build_entity_signal_agreement(claim, reuse_source_location=None)
        assert matrix["location"]["module5_source"] == UNVERIFIABLE


class TestDatetimeAgreement:
    def test_datetime_year_agrees(self):
        claim = _claim(datetime_ref="March 2021")
        matrix = build_entity_signal_agreement(claim, reuse_source_published_at="2021-03-15T00:00:00Z")
        assert matrix["datetime"]["module5_source"] == AGREED

    def test_datetime_year_disagrees(self):
        claim = _claim(datetime_ref="March 2021")
        matrix = build_entity_signal_agreement(claim, reuse_source_published_at="2019-03-15T00:00:00Z")
        assert matrix["datetime"]["module5_source"] == DISAGREED

    def test_datetime_unverifiable_without_source(self):
        claim = _claim(datetime_ref="March 2021")
        matrix = build_entity_signal_agreement(claim, reuse_source_published_at=None)
        assert matrix["datetime"]["module5_source"] == UNVERIFIABLE

    def test_datetime_unverifiable_when_no_year_present(self):
        claim = _claim(datetime_ref="yesterday")
        matrix = build_entity_signal_agreement(claim, reuse_source_published_at="2021-03-15T00:00:00Z")
        assert matrix["datetime"]["module5_source"] == UNVERIFIABLE


class TestBothEntities:
    def test_both_location_and_datetime_present(self):
        claim = _claim(location="Paris", datetime_ref="2021")
        matrix = build_entity_signal_agreement(
            claim,
            reuse_source_location="Paris",
            reuse_source_published_at="2021-01-01",
        )
        assert matrix["location"]["module5_source"] == AGREED
        assert matrix["datetime"]["module5_source"] == AGREED
