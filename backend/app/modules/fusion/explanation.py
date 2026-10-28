"""
modules/fusion/explanation.py — Gemini evidence-grounded explanation (Phase 3).

Rules (architecture.md §Module 7 + video_forensics_tech_spec.md §5):
  NEVER let the LLM guess why something is flagged.
  Pass ONLY validated, structured evidence into the prompt.
  The LLM writes prose — it does NOT make new judgements.

Pattern: ml_exisitng_assets.md — Gemini semantic-validation call (reuse as-is).
Model: gemini-1.5-flash (configurable via GEMINI_MODEL env var).
"""
from __future__ import annotations

import logging
from typing import Optional

from app.modules.fusion.contracts import FusionOutput, AxisResult, Verdict, FusionInput

logger = logging.getLogger(__name__)


# ── Prompt builders ───────────────────────────────────────────────────────────

def _verdict_label(v: Verdict) -> str:
    return v.value.replace("_", " ").title()


def _axis_block(name: str, axis: AxisResult) -> str:
    """Render one axis as a structured evidence block."""
    lines = [
        f"Axis: {name.upper()}",
        f"  Verdict: {_verdict_label(axis.verdict)}",
        f"  Confidence: {axis.confidence:.2f} ({axis.confidence_level.value})",
    ]
    for e in axis.evidence:
        lines.append(f"  Evidence: {e}")
    return "\n".join(lines)


def build_explanation_prompt(
    output: FusionOutput,
    claim_text: Optional[str],
    fusion_inp: Optional[FusionInput] = None,
) -> str:
    """
    Build the Gemini prompt from validated, pre-computed axis results.

    Additional structured evidence drawn from:
      - Module 3's concrete_evidence[] strings (video tri-stream findings)
      - Module 6's evidence_items (top-3 web sources)
    These are already validated by their respective modules; we surface them
    verbatim to the LLM rather than asking it to interpret raw media.
    """
    claim_block = (
        f'Claim under investigation: "{claim_text}"'
        if claim_text
        else "(No explicit claim provided — media-only analysis)"
    )

    axes_text = "\n\n".join([
        _axis_block("Claim Veracity",          output.veracity),
        _axis_block("Media Authenticity",       output.authenticity),
        _axis_block("Cross-Modal Consistency",  output.consistency),
        _axis_block("Historical Reuse",         output.reuse),
    ])

    # ── Optional: video concrete_evidence (Module 3) ──────────────────────────
    video_block = ""
    if fusion_inp and fusion_inp.video_findings:
        vf = fusion_inp.video_findings
        if vf.concrete_evidence:
            lines = "\n".join(f"  - {e}" for e in vf.concrete_evidence[:5])
            video_block = (
                f"\nVideo forensics detail (tri-stream engine output):\n{lines}"
            )

    # ── Optional: Module 6 top evidence items ─────────────────────────────────
    claim_block_detail = ""
    if fusion_inp and fusion_inp.claim_findings:
        cf = fusion_inp.claim_findings
        items = cf.evidence_items[:3]
        if items:
            lines = "\n".join(
                f"  [{i.get('stance','?').upper()}] {i.get('snippet','')[:100]} ({i.get('source_url','')})"
                for i in items
            )
            claim_block_detail = f"\nTop fact-check evidence:\n{lines}"

    prompt = f"""You are a misinformation analyst writing a concise, evidence-grounded report.

{claim_block}

Below are the findings from four independent analysis axes. Each verdict and piece of
evidence has already been validated by the detection pipeline — do NOT add new
judgements, speculate, or invent details not present in the evidence below.
{video_block}{claim_block_detail}

{axes_text}

Write a 3–4 sentence summary that:
1. States what was verified as true (if anything).
2. Names the specific false or contradicted detail (if any), citing the evidence above.
3. Notes what could NOT be checked (any NOT_ASSESSED or INCONCLUSIVE axes).
4. Explains how manipulation, AI-generation, or reuse findings affect the overall picture.

Write in plain language suitable for a non-expert reader. Do not use bullet points.
Do not invent any finding not present in the evidence above."""

    return prompt


# ── Gemini call ───────────────────────────────────────────────────────────────

async def generate_explanation(
    output: FusionOutput,
    claim_text: Optional[str] = None,
    fusion_inp: Optional[FusionInput] = None,
) -> str:
    """
    Call Gemini to turn validated evidence into a readable explanation.
    Returns a plain string. Falls back gracefully if the API is unavailable.
    """
    try:
        from app.core.config import settings
    except Exception:
        return _fallback_explanation(output)

    if not settings.GEMINI_API_KEY:
        logger.debug("GEMINI_API_KEY not set — using fallback explanation.")
        return _fallback_explanation(output)

    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model  = genai.GenerativeModel(settings.GEMINI_MODEL)
        prompt = build_explanation_prompt(output, claim_text, fusion_inp)

        response = await model.generate_content_async(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.2,          # low temp: factual, not creative
                max_output_tokens=300,
            ),
        )
        text = response.text.strip()
        if not text:
            raise ValueError("Empty response from Gemini.")
        return text

    except Exception as exc:    # noqa: BLE001
        logger.warning("Gemini explanation call failed (%s) — using fallback.", exc)
        return _fallback_explanation(output) + f" [Note: explanation model unavailable — {exc}]"


# ── Rule-based fallback ───────────────────────────────────────────────────────

def _fallback_explanation(output: FusionOutput) -> str:
    """
    Structured rule-based explanation when Gemini is unavailable.
    Produces a plain-language per-axis summary from already-computed results.
    """
    parts: list[str] = []
    for name, axis in [
        ("Claim veracity",          output.veracity),
        ("Media authenticity",      output.authenticity),
        ("Cross-modal consistency", output.consistency),
        ("Historical reuse",        output.reuse),
    ]:
        label = _verdict_label(axis.verdict)
        conf  = f"{axis.confidence:.0%}"
        # Add one key evidence item if available
        key_ev = axis.evidence[0] if axis.evidence else ""
        if key_ev:
            parts.append(f"{name}: {label} ({conf} confidence) — {key_ev}")
        else:
            parts.append(f"{name}: {label} ({conf} confidence).")

    return " | ".join(parts)
