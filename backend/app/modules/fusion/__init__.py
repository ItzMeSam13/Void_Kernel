"""
modules/fusion/__init__.py — Module 7 public entrypoint (Phase 3 active).

Strategy:
  1. Level-1 rules: extreme-confidence detectors short-circuit an axis.
  2. Level-2 weighted fusion: per-axis weighted average when no rule fires.
  3. Gemini explanation: 3–4 sentence evidence-grounded summary.

Phase gates are now ACTIVE for Phase 3.
"""
from __future__ import annotations

import logging

from app.modules.fusion.contracts import FusionInput, FusionOutput, AxisResult, Verdict
from app.modules.fusion.rules import (
    rule_authenticity,
    rule_reuse,
    rule_veracity,
    rule_consistency,
)
from app.modules.fusion.weighted_fusion import (
    fuse_authenticity,
    fuse_veracity,
    fuse_consistency,
    fuse_reuse,
)

logger = logging.getLogger(__name__)

# ── Phase gates (Phase 3: both active) ────────────────────────────────────────
_USE_WEIGHTED_FUSION:    bool = True
_USE_GEMINI_EXPLANATION: bool = True


async def run(inp: FusionInput) -> FusionOutput:
    """
    Module 7 entrypoint.

    Per-axis strategy:
      1. Try Level-1 rule short-circuit.
      2. If no rule fires → Level-2 weighted fusion.
      3. If weighted fusion produces no usable data → INCONCLUSIVE default.
    Then generates a Gemini explanation from the validated per-axis evidence.
    """
    try:
        veracity     = rule_veracity(inp)     or fuse_veracity(inp)
        authenticity = rule_authenticity(inp) or fuse_authenticity(inp)
        consistency  = rule_consistency(inp)  or fuse_consistency(inp)
        reuse        = rule_reuse(inp)        or fuse_reuse(inp)

        output = FusionOutput(
            veracity=veracity,
            authenticity=authenticity,
            consistency=consistency,
            reuse=reuse,
        )

        # ── Gemini explanation ─────────────────────────────────────────────────
        if _USE_GEMINI_EXPLANATION:
            try:
                from app.modules.fusion.explanation import generate_explanation
                output.explanation = await generate_explanation(
                    output, inp.claim_text, fusion_inp=inp
                )
            except Exception as exp_exc:   # noqa: BLE001
                logger.warning("Gemini explanation failed — using fallback: %s", exp_exc)
                from app.modules.fusion.explanation import _fallback_explanation
                output.explanation = _fallback_explanation(output)
        else:
            output.explanation = _fallback_explanation_inline(output)

        output.short_label = _derive_short_label(output)
        return output

    except Exception as exc:    # noqa: BLE001
        logger.exception("Module 7 run() error: %s", exc)
        _inc = _inconclusive()
        return FusionOutput(
            error=str(exc),
            veracity=_inc,
            authenticity=_inc,
            consistency=_inc,
            reuse=_inc,
        )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _inconclusive() -> AxisResult:
    return AxisResult(
        verdict=Verdict.INCONCLUSIVE,
        confidence=0.0,
        evidence=["Insufficient signals to determine verdict."],
    )


def _derive_short_label(output: FusionOutput) -> str:
    """One-liner for the API response card."""
    flags: list[str] = []
    for label, axis in [
        ("Veracity issue",      output.veracity),
        ("Authenticity issue",  output.authenticity),
        ("Consistency mismatch",output.consistency),
        ("Historical reuse",    output.reuse),
    ]:
        if axis.verdict not in (
            Verdict.INCONCLUSIVE,
            Verdict.NOT_ASSESSED,
            Verdict.LIKELY_AUTHENTIC,
            Verdict.SUPPORTED,
        ):
            flags.append(label)
    if not flags:
        return "No strong misinformation signals detected."
    return "Flags: " + ", ".join(flags) + "."


def _fallback_explanation_inline(output: FusionOutput) -> str:
    """Used when Gemini flag is off."""
    parts = []
    for name, axis in [
        ("Veracity",     output.veracity),
        ("Authenticity", output.authenticity),
        ("Consistency",  output.consistency),
        ("Reuse",        output.reuse),
    ]:
        label = axis.verdict.value.replace("_", " ").title()
        parts.append(f"{name}: {label} ({axis.confidence:.0%}).")
    return " | ".join(parts)
