"""
Module 5 — run.py
Single public entrypoint: run(input: ReuseInput) -> ReuseFindings

Architecture §6 rule:
  - This is the *entire* interface surface of Module 5.
  - No other module imports anything else from this package.
  - Callable standalone (zero orchestration framework needed).

Phase 1 flow:
  1. Compute SHA-256 + pHash fingerprints.
  2. SHA-256 exact-match lookup (O(1)).
  3. pHash Hamming scan (candidates within MODIFIED threshold).
  4. Merge and deduplicate matches.
  5. (Optional) SerpApi reverse-image search if flag is set.
  6. Return ReuseFindings.

Any exception in steps 2–5 is caught; error is reported in
ReuseFindings.error (Guiding Principle 4: fail honest, never silent).
"""
from __future__ import annotations

from .contracts import ReuseFindings, ReuseInput
from .hashing import fingerprint
from .reference_store import lookup_by_sha256, lookup_by_phash
from .reverse_search import reverse_image_search


def run(inp: ReuseInput) -> ReuseFindings:
    """
    Module 5 entrypoint.

    Accepts a ReuseInput (image_bytes XOR image_path).
    Returns ReuseFindings.  Never raises — errors are surfaced in
    ReuseFindings.error per Guiding Principle 4.
    """
    # Resolve image_data for hashing
    image_data = inp.image_bytes if inp.image_bytes is not None else inp.image_path
    if image_data is None:
        return ReuseFindings(
            reused=False,
            query_sha256="",
            query_phash="",
            error="ReuseInput must have either image_bytes or image_path set.",
        )

    # --- Step 1: fingerprint -------------------------------------------------
    try:
        sha256, phash = fingerprint(image_data)
    except Exception as exc:
        return ReuseFindings(
            reused=False,
            query_sha256="",
            query_phash="",
            error=f"Fingerprinting failed: {exc}",
        )

    all_matches = []
    error_msg = None

    # --- Step 2: SHA-256 exact match -----------------------------------------
    try:
        sha_match = lookup_by_sha256(sha256)
        if sha_match:
            all_matches.append(sha_match)
    except Exception as exc:
        error_msg = f"SHA-256 lookup failed: {exc}"

    # --- Step 3: pHash Hamming scan ------------------------------------------
    phash_matches = []
    try:
        phash_matches = lookup_by_phash(phash, modality=inp.modality)
    except Exception as exc:
        error_msg = (error_msg or "") + f" | pHash scan failed: {exc}"

    # Merge: skip pHash hits whose reference_id was already found by SHA-256
    existing_ids = {m.reference_id for m in all_matches}
    for pm in phash_matches:
        if pm.reference_id not in existing_ids:
            all_matches.append(pm)
            existing_ids.add(pm.reference_id)

    # Sort by Hamming distance ascending (SHA-256 hits have distance=0)
    all_matches.sort(key=lambda m: m.phash_hamming)

    # --- Step 4: optional reverse-image search --------------------------------
    reverse_results: list[dict] = []
    reverse_used = False
    try:
        if inp.image_path:
            reverse_results = reverse_image_search(image_path=inp.image_path)
        elif inp.image_bytes is not None:
            # SerpApi doesn't accept raw bytes directly without a file; skip.
            pass
        reverse_used = bool(reverse_results)
    except Exception as exc:
        error_msg = (error_msg or "") + f" | Reverse search failed: {exc}"

    # --- Step 5: determine reused flag ----------------------------------------
    # "reused" = at least one SAME or MODIFIED match found
    from .contracts import HammingTier
    reused = any(
        m.hamming_tier in (HammingTier.SAME, HammingTier.MODIFIED)
        for m in all_matches
    ) or bool(reverse_results)

    best_match = all_matches[0] if all_matches else None

    return ReuseFindings(
        reused=reused,
        best_match=best_match,
        all_matches=all_matches,
        query_sha256=sha256,
        query_phash=phash,
        reverse_search_used=reverse_used,
        reverse_search_results=reverse_results,
        error=error_msg,
    )
