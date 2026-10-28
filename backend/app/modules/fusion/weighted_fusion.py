"""
modules/fusion/weighted_fusion.py — Level-2 per-axis weighted fusion (Phase 3).

When Level-1 rules don't short-circuit an axis, this file does a
weighted-average over that axis's available detector scores.

Key architecture rules (architecture.md §Module 7):
  - spectral_artifact_score  → raw axis EVIDENCE for authenticity (weight = 0.30)
  - signal_integrity_score   → confidence MODIFIER applied AFTER fusion;
                               never enters the weighted average as axis input.
  - confounded_by_recompression → when True, verdict degrades to INCONCLUSIVE
                               regardless of what the weighted average says.
  - Do NOT fuse across axes.  Four axes, four independent AxisResults.

Weights are hand-tuned starting values (Veritas Score Aggregator style).
Upgrade path: per-axis XGBoost head once labeled fusion data is available.
(architecture.md Module 7: "document_forgery's XGBoost-for-explainability
is the right fallback, not a mandatory day-one build")
"""
from __future__ import annotations

import logging
from typing import Optional

from app.modules.fusion.contracts import (
    FusionInput,
    Verdict,
    AxisResult,
    ConfidenceLevel,
)

logger = logging.getLogger(__name__)


# ── Weights ───────────────────────────────────────────────────────────────────
# Weights within an axis sum to 1.0 for present features.
# Absent features are excluded and the remaining weights are re-normalised.

AUTHENTICITY_WEIGHTS: dict[str, float] = {
    "smaug_ai_score":             0.35,
    "spectral_artifact_score":    0.30,   # GAN/diffusion evidence (not signal_integrity!)
    "manipulation_confidence":    0.25,
    "synthetic_audio_confidence": 0.10,
}

VERACITY_WEIGHTS: dict[str, float] = {
    "overall_confidence": 1.0,            # Module 6 is the sole veracity scorer
}

CONSISTENCY_WEIGHTS: dict[str, float] = {
    "clip_similarity_score": 0.70,
    "synthetic_text_score":  0.30,        # Module 2B score as consistency signal
}

REUSE_WEIGHTS: dict[str, float] = {
    "phash_score": 1.0,                   # converted from Hamming distance below
}


# ── Shared helpers ────────────────────────────────────────────────────────────

def _level(confidence: float) -> ConfidenceLevel:
    if confidence >= 0.75:
        return ConfidenceLevel.HIGH
    if confidence >= 0.50:
        return ConfidenceLevel.MEDIUM
    if confidence >= 0.25:
        return ConfidenceLevel.LOW
    return ConfidenceLevel.NONE


def _weighted_average(
    scores: dict[str, float],
    weights: dict[str, float],
) -> tuple[float, dict[str, tuple[float, float]]]:
    """
    Normalised weighted average of *scores* (skips missing / None values).

    Returns:
      (weighted_avg, {feature: (score, effective_weight)})
    """
    total_w = 0.0
    total_s = 0.0
    used: dict[str, tuple[float, float]] = {}

    for key, w in weights.items():
        val = scores.get(key)
        if val is None:
            continue
        total_w += w
        total_s += val * w
        used[key] = (val, w)

    if total_w == 0.0:
        return 0.0, {}

    avg = total_s / total_w
    # Re-normalise effective weights for display
    renorm = {k: (v, w / total_w) for k, (v, w) in used.items()}
    return avg, renorm


def _evidence_lines(used: dict[str, tuple[float, float]]) -> list[str]:
    """Format contributing scores as human-readable evidence strings."""
    return [
        f"{feat}={val:.3f} (normalised weight={wt:.2f})"
        for feat, (val, wt) in used.items()
    ]


# ══════════════════════════════════════════════════════════════════════════════
# AUTHENTICITY axis
# ══════════════════════════════════════════════════════════════════════════════

def fuse_authenticity(inp: FusionInput) -> AxisResult:
    """
    Weighted fusion for the media-authenticity axis.

    spectral_artifact_score  → axis evidence (enters weighted average)
    signal_integrity_score   → confidence MODIFIER applied AFTER the average
                               (never enters the weighted average)
    confounded_by_recompression → if True, verdict degrades to INCONCLUSIVE
    """
    img = inp.image_findings
    vid = inp.video_findings
    aud = inp.audio_findings

    # ── Collect axis evidence scores ──────────────────────────────────────────
    raw: dict[str, Optional[float]] = {
        "smaug_ai_score": img.smaug_ai_score if img else None,

        # spectral_artifact_score is axis EVIDENCE (periodic GAN checkerboard)
        "spectral_artifact_score": vid.spectral_artifact_score if vid else None,

        "manipulation_confidence": img.manipulation_confidence if img else None,

        # Synthetic audio: only count when detector is positive
        "synthetic_audio_confidence": (
            aud.synthetic_audio_confidence
            if aud and aud.synthetic_audio_signal == "synthetic_audio_signal_detected"
            else None
        ),
    }

    scores = {k: v for k, v in raw.items() if v is not None}
    avg, used = _weighted_average(scores, AUTHENTICITY_WEIGHTS)
    evidence  = _evidence_lines(used)

    if not evidence:
        return AxisResult(
            verdict=Verdict.NOT_ASSESSED,
            evidence=["No authenticity signals available."],
        )

    # ── Map average → verdict ─────────────────────────────────────────────────
    if avg > 0.70:
        verdict = Verdict.LIKELY_AI_GENERATED
    elif avg > 0.55:
        verdict = Verdict.LIKELY_MANIPULATED
    elif avg < 0.30:
        verdict = Verdict.LIKELY_AUTHENTIC
    else:
        verdict = Verdict.INCONCLUSIVE

    confidence = avg

    # ── Apply signal_integrity confidence modifier (architecture.md §Module 7) ─
    # signal_integrity_score is broadband recompression artefact energy.
    # High value means the authenticity verdict is confounded — downgrade it.
    if vid and vid.confounded_by_recompression:
        si_str = f"{vid.signal_integrity_score:.3f}" if vid.signal_integrity_score is not None else "?"
        evidence.append(
            f"signal_integrity_score={si_str} — "
            "broadband recompression artefacts present; verdict downgraded to INCONCLUSIVE."
        )
        confidence *= 0.6
        verdict     = Verdict.INCONCLUSIVE
    elif vid and vid.signal_integrity_score is not None and vid.signal_integrity_score > 0.5:
        # Moderate recompression signal: penalise confidence but don't force INCONCLUSIVE
        penalty = (vid.signal_integrity_score - 0.5) * 0.4   # 0–0.2 penalty
        confidence = max(0.0, confidence - penalty)
        evidence.append(
            f"signal_integrity_score={vid.signal_integrity_score:.3f} — "
            f"moderate recompression signal; confidence penalised by {penalty:.2f}."
        )

    return AxisResult(
        verdict=verdict,
        confidence=round(confidence, 4),
        confidence_level=_level(confidence),
        evidence=evidence,
        contributing_scores={k: v for k, v in raw.items() if v is not None},
    )


# ══════════════════════════════════════════════════════════════════════════════
# VERACITY axis
# ══════════════════════════════════════════════════════════════════════════════

def fuse_veracity(inp: FusionInput) -> AxisResult:
    """
    Weighted fusion for claim veracity.
    Module 6 is the sole veracity scorer; echo-chamber flag applies 0.75× penalty.
    """
    cf = inp.claim_findings
    if cf is None or cf.overall_verdict == Verdict.NOT_ASSESSED:
        return AxisResult(
            verdict=Verdict.NOT_ASSESSED,
            evidence=["Module 6 fact-checking not available for this input."],
        )

    confidence = cf.overall_confidence
    evidence: list[str] = []

    if cf.echo_chamber_flag:
        confidence *= 0.75
        evidence.append(
            f"Echo-chamber flag: confidence penalised by 0.75× "
            f"(original={cf.overall_confidence:.3f}, adjusted={confidence:.3f})."
        )

    if cf.drift_guard_similarity is not None and cf.drift_guard_similarity < 0.7:
        evidence.append(
            f"Essence drift guard: claim-text similarity={cf.drift_guard_similarity:.3f} — "
            "extracted claims may have drifted from original input; treat veracity with caution."
        )

    # Top-3 evidence items
    for item in cf.evidence_items[:3]:
        stance  = item.get("stance", "?").upper()
        snippet = item.get("snippet", "")[:150]
        src     = item.get("source_url", "")
        evidence.append(f"[{stance}] {snippet} — {src}")

    # Entity agreement matrix flags
    for entity, signals in cf.entity_agreement_matrix.items():
        if isinstance(signals, dict) and signals.get("conflict"):
            evidence.append(f"Entity conflict — {entity}: {signals.get('detail', '')}")

    return AxisResult(
        verdict=cf.overall_verdict,
        confidence=round(confidence, 4),
        confidence_level=_level(confidence),
        evidence=evidence,
        contributing_scores={
            "overall_confidence": cf.overall_confidence,
            "echo_chamber_flag":  cf.echo_chamber_flag,
            "drift_guard_similarity": cf.drift_guard_similarity,
        },
    )


# ══════════════════════════════════════════════════════════════════════════════
# CONSISTENCY axis
# ══════════════════════════════════════════════════════════════════════════════

def fuse_consistency(inp: FusionInput) -> AxisResult:
    """
    Weighted fusion for cross-modal consistency (claim vs. image/audio).

    CLIP similarity: low score = mismatch → inverted before fusion so
                     a higher fused score = more suspicious.
    Module 2B synthetic-text score: high = AI-generated text = suspicious.
    """
    img        = inp.image_findings
    synth_text = inp.synthetic_text_findings

    clip  = img.clip_similarity_score if img else None
    synth = (
        synth_text.score
        if synth_text and synth_text.verdict != "not_assessed" and synth_text.score is not None
        else None
    )

    evidence: list[str] = []
    raw_scores: dict[str, float] = {}

    if clip is not None:
        raw_scores["clip_similarity_score"] = clip
        evidence.append(f"CLIP claim-image similarity={clip:.3f}")

    if synth is not None:
        raw_scores["synthetic_text_score"] = synth
        verdict_tag = synth_text.verdict if synth_text else "?"   # type: ignore[union-attr]
        evidence.append(f"Synthetic text score={synth:.3f} ({verdict_tag})")

    if not raw_scores:
        return AxisResult(
            verdict=Verdict.NOT_ASSESSED,
            evidence=["No consistency signals available (CLIP / Module 2B)."],
        )

    # Invert CLIP so higher fused score = more suspicious mismatch
    inverted = {
        k: (1.0 - v if k == "clip_similarity_score" else v)
        for k, v in raw_scores.items()
    }
    avg, _ = _weighted_average(inverted, CONSISTENCY_WEIGHTS)

    if avg > 0.65:
        verdict = Verdict.CONTRADICTED
    elif avg < 0.35:
        verdict = Verdict.SUPPORTED
    else:
        verdict = Verdict.UNCERTAIN

    return AxisResult(
        verdict=verdict,
        confidence=round(avg, 4),
        confidence_level=_level(avg),
        evidence=evidence,
        contributing_scores=raw_scores,
    )


# ══════════════════════════════════════════════════════════════════════════════
# REUSE axis
# ══════════════════════════════════════════════════════════════════════════════

def fuse_reuse(inp: FusionInput) -> AxisResult:
    """
    Weighted fusion for historical out-of-context reuse.

    Hamming distance is converted to a 0–1 similarity score:
      distance 0  → similarity 1.0  (exact visual match)
      distance 15 → similarity 0.0  (boundary between modified / different)
    """
    r = inp.reuse_findings
    if r is None:
        return AxisResult(
            verdict=Verdict.NOT_ASSESSED,
            evidence=["Module 5 historical reuse check not available."],
        )

    # ── Definitive tiers (should have been caught by Level-1, but be robust) ──
    if r.exact_match:
        evidence = [
            f"SHA-256 exact match — previously seen at: "
            f"{r.source_url or 'unknown'} "
            f"(published: {r.source_published_at or 'unknown'})."
        ]
        if r.source_location:
            evidence.append(f"Source location: {r.source_location}.")
        return AxisResult(
            verdict=Verdict.CONTRADICTED,
            confidence=1.0,
            confidence_level=ConfidenceLevel.HIGH,
            evidence=evidence,
            contributing_scores={"exact_match": True},
        )

    if r.reuse_tier == "different" or (
        r.phash_hamming_distance is not None and r.phash_hamming_distance > 15
    ):
        return AxisResult(
            verdict=Verdict.LIKELY_AUTHENTIC,
            confidence=0.85,
            confidence_level=ConfidenceLevel.HIGH,
            evidence=["pHash distance > 15 — no visual match found in reference store."],
            contributing_scores={"phash_hamming_distance": r.phash_hamming_distance},
        )

    # ── Modified tier: weighted pHash score ───────────────────────────────────
    if r.reuse_tier == "modified" and r.phash_hamming_distance is not None:
        d           = r.phash_hamming_distance
        # Map distance 5–15 → similarity 0.85–0.0
        phash_score = max(0.0, 0.85 - (d - 5) * (0.85 / 10))
        avg, _      = _weighted_average({"phash_score": phash_score}, REUSE_WEIGHTS)

        evidence = [
            f"pHash Hamming distance={d} (tier=modified, 5–15) — "
            f"possible out-of-context reuse (similarity={phash_score:.2f})."
        ]
        if r.source_url:
            evidence.append(
                f"Potential source: {r.source_url} "
                f"(published {r.source_published_at or 'unknown'})."
            )
        if r.source_location:
            evidence.append(f"Source location: {r.source_location}.")

        return AxisResult(
            verdict=Verdict.CONTRADICTED,
            confidence=round(avg, 4),
            confidence_level=_level(avg),
            evidence=evidence,
            contributing_scores={"phash_hamming_distance": d, "phash_score": phash_score},
        )

    # Fallback
    return AxisResult(
        verdict=Verdict.INCONCLUSIVE,
        evidence=["pHash result inconclusive — no tier assigned."],
    )
