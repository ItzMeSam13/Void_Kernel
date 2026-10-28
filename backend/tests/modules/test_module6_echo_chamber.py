"""
E2E tests for Module 6 — Phase 3 echo-chamber detection (web_search.py)
and the confidence-multiplier wiring in evidence_judge.py.
"""
from __future__ import annotations

from app.modules.factcheck.web_search import (
    ECHO_CHAMBER_CONFIDENCE_MULTIPLIER,
    detect_echo_chamber,
    root_domain,
)


class TestRootDomain:
    def test_strips_www_prefix(self):
        assert root_domain({"url": "https://www.example.com/a"}) == "example.com"

    def test_keeps_non_www_netloc(self):
        assert root_domain({"url": "https://news.example.com/a"}) == "news.example.com"

    def test_falls_back_to_source_url_key(self):
        assert root_domain({"source_url": "https://foo.org/x"}) == "foo.org"

    def test_missing_url_returns_empty(self):
        assert root_domain({}) == ""


class TestDetectEchoChamber:
    def test_no_hits_not_flagged(self):
        flagged, unique_count, dominant = detect_echo_chamber([])
        assert flagged is False
        assert unique_count == 0
        assert dominant == set()

    def test_diverse_domains_not_flagged(self):
        hits = [
            {"url": "https://a.com/1"},
            {"url": "https://b.com/1"},
            {"url": "https://c.com/1"},
            {"url": "https://d.com/1"},
        ]
        flagged, unique_count, dominant = detect_echo_chamber(hits)
        assert flagged is False
        assert unique_count == 4
        assert dominant == set()

    def test_repeated_domain_triggers_dominant_flag(self):
        hits = [
            {"url": "https://a.com/1"},
            {"url": "https://a.com/2"},
            {"url": "https://a.com/3"},
            {"url": "https://b.com/1"},
            {"url": "https://c.com/1"},
        ]
        flagged, unique_count, dominant = detect_echo_chamber(hits)
        assert flagged is True
        assert dominant == {"a.com"}
        assert unique_count == 3

    def test_fewer_than_three_unique_domains_flagged_even_without_repeat(self):
        hits = [
            {"url": "https://a.com/1"},
            {"url": "https://b.com/1"},
        ]
        flagged, unique_count, dominant = detect_echo_chamber(hits)
        assert flagged is True
        assert unique_count == 2
        assert dominant == set()  # neither domain individually hit the repeat threshold


class TestEchoChamberConfidenceMultiplier:
    def test_multiplier_value_matches_architecture_spec(self):
        assert ECHO_CHAMBER_CONFIDENCE_MULTIPLIER == 0.75
