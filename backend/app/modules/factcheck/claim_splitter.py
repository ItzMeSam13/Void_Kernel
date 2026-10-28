"""
Module 6 — claim_splitter.py
Splits raw input text into atomic, checkable claims.

Phase 1 scope (team_roadmaps.md):
  - Claim splitting + Veritas-ported claim_type / loaded_language tagging.

Phase 3 scope (team_roadmaps.md):
  - NER entity-tagging (location/datetime/named_people/event), extending
    the Veritas-ported fields above. This is what makes the entity x
    signal agreement matrix (architecture.md §Module 6, step 7;
    entity_crosscheck.py) possible — without entity tags there is
    nothing concrete to cross-reference against Module 5's source
    metadata.

Architecture reference:
  - Reuse Veritas's `type: fact | framing | attributed` tagging and
    `loaded_language` extraction (architecture.md §Module 6, step 1).
  - Uses Gemini for splitting (same Gemini call pattern as document_forgery
    text_forensics_engine.py, per Asset Reuse Matrix).

Isolation rule (§6): this file only knows about the contracts in this
module. It does NOT import from any other module.
"""
from __future__ import annotations

import json
import re
import uuid
import warnings
from functools import lru_cache

from .contracts import AtomicClaim, ClaimType
from .llm_client import generate

# ---------------------------------------------------------------------------
# [PHASE-3] NER entity-tagging
# ---------------------------------------------------------------------------

_NER_MODEL_NAME = "en_core_web_sm"

# spaCy's standard NER labels map directly onto the schema's entity fields.
# Location itself is handled separately below (GPE preferred over LOC).
_DATETIME_LABELS = ("DATE", "TIME")
_PERSON_LABEL = "PERSON"
_EVENT_LABEL = "EVENT"


@lru_cache(maxsize=1)
def _get_nlp():
    """Lazily load the spaCy pipeline once per process."""
    import spacy

    try:
        return spacy.load(_NER_MODEL_NAME)
    except OSError as exc:
        raise RuntimeError(
            f"spaCy model '{_NER_MODEL_NAME}' not installed. "
            f"Run: python -m spacy download {_NER_MODEL_NAME}"
        ) from exc


def _extract_entities(text: str) -> dict:
    """
    Tag `text` with location / datetime_ref / named_people / event_ref.

    Fails open (all fields empty) on any spaCy/model error — Guiding
    Principle 4: fail honest, never block claim splitting on this.
    """
    empty = {"location": None, "datetime_ref": None, "named_people": [], "event_ref": None}
    if not text.strip():
        return empty

    try:
        doc = _get_nlp()(text)
    except Exception as exc:
        warnings.warn(f"[Module6/claim_splitter] NER extraction failed: {exc}")
        return empty

    # GPE (actual place names: cities, countries) is preferred over LOC
    # (landmarks, mountains, bodies of water) for the entity x signal
    # agreement matrix — a landmark name like "The Eiffel Tower" can't be
    # usefully compared against Module 5's source_location, but it would
    # otherwise win just by appearing first in sentence order.
    gpe_locations = [e.text for e in doc.ents if e.label_ == "GPE"]
    loc_locations = [e.text for e in doc.ents if e.label_ == "LOC"]
    locations = gpe_locations or loc_locations
    dates = [e.text for e in doc.ents if e.label_ in _DATETIME_LABELS]
    people = [e.text for e in doc.ents if e.label_ == _PERSON_LABEL]
    events = [e.text for e in doc.ents if e.label_ == _EVENT_LABEL]

    return {
        "location": locations[0] if locations else None,
        "datetime_ref": dates[0] if dates else None,
        "named_people": people,
        "event_ref": events[0] if events else None,
    }


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

_SPLIT_SYSTEM = """You are a precise claim-extraction assistant.
Given a passage of text, identify every distinct, independently
fact-checkable atomic claim it contains.

For each claim return a JSON object with:
  "text"          : the verbatim or minimally-cleaned claim sentence
  "claim_type"    : one of "fact" | "framing" | "attributed"
                    fact       = an objective assertion about the world
                    framing    = an evaluative or interpretive statement
                    attributed = "X said/claimed/reported Y"
  "loaded_language": a list of emotionally loaded or evaluative terms in the claim

Return ONLY a JSON array of these objects, no prose.
Example:
[
  {"text": "The prime minister resigned on Monday.",
   "claim_type": "fact", "loaded_language": []},
  {"text": "The resignation was a cowardly retreat.",
   "claim_type": "framing", "loaded_language": ["cowardly", "retreat"]}
]"""

_SPLIT_USER = "Text to analyse:\n\n{text}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_llm_json(raw: str) -> list[dict]:
    """
    Extract JSON array from LLM response (may be wrapped in markdown fences).

    Uses raw_decode() rather than loads() because smaller local models
    (e.g. phi3:mini via Ollama) sometimes keep generating after a
    well-formed JSON array — echoing the prompt or hallucinating another
    example — instead of stopping cleanly like Gemini does. raw_decode()
    parses just the first JSON value and ignores anything trailing it.
    """
    # Strip ```json ... ``` fences if present
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned).strip()
    obj, _ = json.JSONDecoder().raw_decode(cleaned)
    return obj


def _make_claim(idx: int, raw: dict) -> AtomicClaim:
    claim_type_raw = raw.get("claim_type", "fact").lower()
    try:
        claim_type = ClaimType(claim_type_raw)
    except ValueError:
        claim_type = ClaimType.FACT  # safe default

    entities = _extract_entities(raw["text"])

    return AtomicClaim(
        claim_id=f"c{idx + 1}_{uuid.uuid4().hex[:6]}",
        text=raw["text"],
        claim_type=claim_type,
        loaded_language=raw.get("loaded_language", []),
        **entities,
    )


# ---------------------------------------------------------------------------
# Public function
# ---------------------------------------------------------------------------

def split_claims(text: str) -> list[AtomicClaim]:
    """
    Split `text` into a list of AtomicClaim objects.

    Uses llm_client.generate() — local Ollama by default, swappable to
    Gemini via FACTCHECK_LLM_BACKEND (see llm_client.py).

    Falls back to returning the full text as a single untyped FACT claim
    if the LLM call fails, rather than raising — the pipeline continues
    with reduced precision (Guiding Principle 4).
    """
    if not text.strip():
        return []

    try:
        raw_text = generate(_SPLIT_SYSTEM, _SPLIT_USER.format(text=text))
        raw_list = _parse_llm_json(raw_text)
        return [_make_claim(i, r) for i, r in enumerate(raw_list) if "text" in r]

    except Exception as exc:
        warnings.warn(f"[Module6/claim_splitter] LLM call failed: {exc}. Falling back.")
        return [
            AtomicClaim(
                claim_id=f"c1_{uuid.uuid4().hex[:6]}",
                text=text,
                claim_type=ClaimType.FACT,
                loaded_language=[],
                **_extract_entities(text),
            )
        ]
