"""
Module 6 — entity_crosscheck.py
Entity x signal agreement matrix (Phase 3 [Improvement],
architecture.md §Module 6, step 7).

Scope, deliberately shallow per architecture.md's own tradeoff note:
  "When no source is found anywhere (Module 5 empty, Tavily empty), the
   entity-level check reports unverifiable, not a guess. This is the
   explicit tradeoff of staying shallow: it reliably catches *reused*
   media with a findable prior source, and is honest about not catching
   a genuinely novel wrong-context fabrication that's never been posted
   before."

Only one signal is wired in Phase 3: Module 5's source metadata
(reuse_source_location / reuse_source_published_at), passed in via
FactCheckInput and forwarded here per-claim by run.py. Entities with no
comparable Module 5 field, or when no Module 5 match exists at all, are
reported "unverifiable" — never a guess (Guiding Principle 4).

Isolation rule (§6): takes an AtomicClaim + plain strings, returns a
plain dict. No knowledge of orchestration or other modules.
"""
from __future__ import annotations

import re
from typing import Optional

from .contracts import AtomicClaim

AGREED = "agreed"
DISAGREED = "disagreed"
UNVERIFIABLE = "unverifiable"

_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _location_agreement(claim_location: str, source_location: Optional[str]) -> str:
    if not source_location:
        return UNVERIFIABLE
    claim_norm, source_norm = _normalize(claim_location), _normalize(source_location)
    if claim_norm in source_norm or source_norm in claim_norm:
        return AGREED
    # A stated-but-different location is a disagreement — shallow but honest.
    return DISAGREED


def _datetime_agreement(claim_datetime: str, source_published_at: Optional[str]) -> str:
    if not source_published_at:
        return UNVERIFIABLE

    claim_year = _YEAR_RE.search(claim_datetime)
    source_year = _YEAR_RE.search(source_published_at)
    if not claim_year or not source_year:
        # Relative references ("yesterday", "last week") can't be resolved
        # to an absolute date without a submission timestamp — stay honest
        # rather than guess.
        return UNVERIFIABLE

    return AGREED if claim_year.group(0) == source_year.group(0) else DISAGREED


def build_entity_signal_agreement(
    claim: AtomicClaim,
    reuse_source_location: Optional[str] = None,
    reuse_source_published_at: Optional[str] = None,
) -> Optional[dict]:
    """
    Build the entity x signal agreement matrix for one claim against
    Module 5's source metadata.

    Returns None when the claim carries no NER-tagged location/datetime
    (nothing to check). Otherwise returns e.g.:
      {"location": {"module5_source": "disagreed"},
       "datetime": {"module5_source": "unverifiable"}}
    """
    matrix: dict[str, dict[str, str]] = {}

    if claim.location:
        matrix["location"] = {
            "module5_source": _location_agreement(claim.location, reuse_source_location)
        }
    if claim.datetime_ref:
        matrix["datetime"] = {
            "module5_source": _datetime_agreement(claim.datetime_ref, reuse_source_published_at)
        }

    return matrix or None
