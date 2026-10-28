"""
modules/fusion/rules.py — Level-1 rule-based fusion (Phase 1).

Level-1 rule engine:
  • Evaluates extreme-confidence detectors first.
  • Short-circuits an axis to a strong verdict WITHOUT waiting for ML fusion.
  • Returns None for an axis when no rule fires → falls through to Level-2.

Each rule function returns (Verdict, confidence, evidence_strings) or None.

Rules are intentionally conservative: a rule fires only when a single
detector is at a threshold that makes the ML step redundant (e.g. exact
SHA-256 match, Smaug > 0.95, reuse tier == "same").

architecture.md §Module 7 — Level 1 rules spec:
  "any single detector at extreme confidence short-circuits that axis to a
   strong verdict without waiting on ML fusion"
"""
from __future__ import annotations

from typing import Optional

from app.modules.fusion.contracts import (
    FusionInput,
    Verdict,
    AxisResult,
    ConfidenceLevel,
)


# ─── Thresholds ───────────────────────────────────────────────────────────────
SMAUG_HIGH_CONFIDENCE   = 0.95   # AI-generated image almost certain
MANIPULATION_HIGH       = 0.90   # Manipulation detector very confident
CLIP_MISMATCH_LOW       = 0.15   # Very low CLIP → strong inconsistency signal
SYNTHETIC_AUDIO_HIGH    = 0.90   # Wav2Vec2 very confident on synthetic audio
DEBERTA_CONTRADICTED    = 0.90   # DeBERTa NLI strongly contradicts claim


def _level(confidence: float) -> ConfidenceLevel:
    if confidence >= 0.85:
        return ConfidenceLevel.HIGH
    if confidence >= 0.60:
        return ConfidenceLevel.MEDIUM
    if confidence >= 0.35:
        return ConfidenceLevel.LOW
    return ConfidenceLevel.NONE


# ══════════════════════════════════════════════════════════════════════════════
# Axis: AUTHENTICITY
# Evidence: Smaug (AI-gen), ManTraNet manipulation, spectral_artifact_score,
#           synthetic_audio_signal
# Confidence modifier: signal_integrity_score / confounded_by_recompression
# ══════════════════════════════════════════════════════════════════════════════

def rule_authenticity(inp: FusionInput) -> Optional[AxisResult]:
    """
    Short-circuit authenticity axis if any single detector is extreme.
    Spectral split handled exactly per architecture.md Module 7:
      - spectral_artifact_score → axis evidence
      - signal_integrity_score  → confidence modifier (may downgrade to INCONCLUSIVE)
    """
    evidence: list[str] = []
    verdict = None
    raw_confidence = 0.0

    img = inp.image_findings
    vid = inp.video_findings
    aud = inp.audio_findings

    # ── Rule A1: Smaug AI-image extreme ─────────────────────────────────────
    if img and img.smaug_ai_score is not None and img.smaug_ai_score > SMAUG_HIGH_CONFIDENCE:
        verdict = Verdict.LIKELY_AI_GENERATED
        raw_confidence = img.smaug_ai_score
        evidence.append(
            f"Smaug AI-image detector: score={img.smaug_ai_score:.3f} "
            f"(threshold={SMAUG_HIGH_CONFIDENCE}) — high confidence of AI generation."
        )

    # ── Rule A2: ManTraNet manipulation extreme ───────────────────────────────
    if (img and img.manipulation_detected and
            img.manipulation_confidence is not None and
            img.manipulation_confidence > MANIPULATION_HIGH):
        if verdict is None or raw_confidence < img.manipulation_confidence:
            verdict = Verdict.LIKELY_MANIPULATED
            raw_confidence = img.manipulation_confidence
        evidence.append(
            f"Manipulation detector: confidence={img.manipulation_confidence:.3f} "
            f"(threshold={MANIPULATION_HIGH}) — strong manipulation signal."
        )

    # ── Rule A3: Spectral artifact score (video) ─────────────────────────────
    if vid and vid.spectral_artifact_score is not None and vid.spectral_artifact_score > SMAUG_HIGH_CONFIDENCE:
        if verdict is None or raw_confidence < vid.spectral_artifact_score:
            verdict = Verdict.LIKELY_AI_GENERATED
            raw_confidence = vid.spectral_artifact_score
        evidence.append(
            f"Spectral artifact score (periodic GAN checkerboard): "
            f"{vid.spectral_artifact_score:.3f} — GAN/diffusion evidence."
        )

    # ── Rule A4: Synthetic audio signal extreme ───────────────────────────────
    if (aud and aud.synthetic_audio_signal == "synthetic_audio_signal_detected" and
            aud.synthetic_audio_confidence is not None and
            aud.synthetic_audio_confidence > SYNTHETIC_AUDIO_HIGH):
        if verdict is None:
            verdict = Verdict.LIKELY_AI_GENERATED
            raw_confidence = aud.synthetic_audio_confidence
        evidence.append(
            f"Wav2Vec2 deepfake-audio: confidence={aud.synthetic_audio_confidence:.3f} — "
            f"synthetic audio signal detected."
        )

    if verdict is None:
        return None  # no rule fired → fall through to Level-2

    # ── Apply signal_integrity confidence modifier ────────────────────────────
    if vid and vid.confounded_by_recompression:
        evidence.append(
            f"signal_integrity_score={vid.signal_integrity_score:.3f} is high — "
            f"broadband recompression artefacts confound spectral verdict; "
            f"downgrading to INCONCLUSIVE."
        )
        return AxisResult(
            verdict=Verdict.INCONCLUSIVE,
            confidence=raw_confidence * 0.4,   # significant downgrade
            confidence_level=ConfidenceLevel.LOW,
            evidence=evidence,
            contributing_scores=_contributing_scores(inp, "authenticity"),
        )

    return AxisResult(
        verdict=verdict,
        confidence=raw_confidence,
        confidence_level=_level(raw_confidence),
        evidence=evidence,
        contributing_scores=_contributing_scores(inp, "authenticity"),
    )


# ══════════════════════════════════════════════════════════════════════════════
# Axis: REUSE
# Evidence: SHA-256 exact match, pHash tier
# ══════════════════════════════════════════════════════════════════════════════

def rule_reuse(inp: FusionInput) -> Optional[AxisResult]:
    """
    Short-circuit reuse axis on exact SHA-256 hit or tight pHash match.
    """
    r = inp.reuse_findings
    if r is None:
        return None

    evidence: list[str] = []
    verdict = None
    confidence = 0.0

    if r.exact_match:
        verdict = Verdict.CONTRADICTED   # reused media is a strong misinformation signal
        confidence = 1.0
        evidence.append(
            f"SHA-256 exact match — this media was previously seen at: "
            f"{r.source_url or 'unknown source'} "
            f"(published: {r.source_published_at or 'unknown date'})."
        )
    elif r.reuse_tier == "same" and r.phash_hamming_distance is not None:
        verdict = Verdict.CONTRADICTED
        confidence = 0.92
        evidence.append(
            f"pHash Hamming distance={r.phash_hamming_distance} (tier=same, <5) — "
            f"effectively identical media found at: {r.source_url or 'unknown'}."
        )
    elif r.reuse_tier == "modified" and r.phash_hamming_distance is not None:
        # Modified tier alone doesn't short-circuit — needs ML fusion to weigh
        return None

    if verdict is None:
        return None

    if r.source_published_at:
        evidence.append(f"Source publication date: {r.source_published_at}.")
    if r.source_location:
        evidence.append(f"Source reported location: {r.source_location}.")

    return AxisResult(
        verdict=verdict,
        confidence=confidence,
        confidence_level=_level(confidence),
        evidence=evidence,
        contributing_scores=_contributing_scores(inp, "reuse"),
    )


# ══════════════════════════════════════════════════════════════════════════════
# Axis: VERACITY
# Evidence: ClaimFindings overall_verdict
# ══════════════════════════════════════════════════════════════════════════════

def rule_veracity(inp: FusionInput) -> Optional[AxisResult]:
    """
    Short-circuit veracity axis only when Module 6 is extremely confident.
    Low-confidence veracity results go to Level-2 weighted fusion.
    """
    cf = inp.claim_findings
    if cf is None or cf.overall_confidence < DEBERTA_CONTRADICTED:
        return None

    evidence: list[str] = []

    if cf.overall_verdict in (Verdict.SUPPORTED, Verdict.CONTRADICTED):
        for item in cf.evidence_items[:3]:   # top 3 evidence items
            snippet = item.get("snippet", "")
            src = item.get("source_url", "")
            stance = item.get("stance", "")
            evidence.append(f"[{stance.upper()}] {snippet} — source: {src}")

        if cf.echo_chamber_flag:
            evidence.append(
                "Echo-chamber flag: multiple results share the same root domain — "
                "confidence penalised."
            )

        confidence = cf.overall_confidence
        if cf.echo_chamber_flag:
            confidence *= 0.75   # Veritas echo-chamber multiplier

        return AxisResult(
            verdict=cf.overall_verdict,
            confidence=confidence,
            confidence_level=_level(confidence),
            evidence=evidence,
            contributing_scores=_contributing_scores(inp, "veracity"),
        )

    return None


# ══════════════════════════════════════════════════════════════════════════════
# Axis: CONSISTENCY
# Evidence: CLIP similarity, BLIP vs claim
# ══════════════════════════════════════════════════════════════════════════════

def rule_consistency(inp: FusionInput) -> Optional[AxisResult]:
    """
    Short-circuit consistency axis on very low CLIP similarity (strong mismatch).
    """
    img = inp.image_findings
    if img is None or img.clip_similarity_score is None:
        return None

    if img.clip_similarity_score < CLIP_MISMATCH_LOW:
        return AxisResult(
            verdict=Verdict.CONTRADICTED,
            confidence=1.0 - img.clip_similarity_score,
            confidence_level=ConfidenceLevel.HIGH,
            evidence=[
                f"CLIP claim-image similarity={img.clip_similarity_score:.3f} "
                f"(threshold={CLIP_MISMATCH_LOW}) — strong visual mismatch with supplied claim."
            ],
            contributing_scores=_contributing_scores(inp, "consistency"),
        )
    return None


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _contributing_scores(inp: FusionInput, axis: str) -> dict:
    """Collect the raw numeric scores relevant to *axis* for auditability."""
    scores: dict = {}
    if axis == "authenticity":
        if inp.image_findings:
            scores["smaug_ai_score"] = inp.image_findings.smaug_ai_score
            scores["manipulation_confidence"] = inp.image_findings.manipulation_confidence
        if inp.video_findings:
            scores["spectral_artifact_score"] = inp.video_findings.spectral_artifact_score
            scores["signal_integrity_score"]  = inp.video_findings.signal_integrity_score
            scores["confounded_by_recompression"] = inp.video_findings.confounded_by_recompression
        if inp.audio_findings:
            scores["synthetic_audio_confidence"] = inp.audio_findings.synthetic_audio_confidence
    elif axis == "veracity":
        if inp.claim_findings:
            scores["overall_confidence"] = inp.claim_findings.overall_confidence
            scores["echo_chamber_flag"]  = inp.claim_findings.echo_chamber_flag
    elif axis == "consistency":
        if inp.image_findings:
            scores["clip_similarity_score"] = inp.image_findings.clip_similarity_score
    elif axis == "reuse":
        if inp.reuse_findings:
            scores["exact_match"]             = inp.reuse_findings.exact_match
            scores["phash_hamming_distance"]  = inp.reuse_findings.phash_hamming_distance
            scores["reuse_tier"]              = inp.reuse_findings.reuse_tier
    return scores
