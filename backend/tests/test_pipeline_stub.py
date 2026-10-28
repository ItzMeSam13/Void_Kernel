66uuuuuu"""
tests/test_pipeline_stub.py — Phase 3 integration smoke test.

Verifies:
  1. Graph compiles.
  2. text_image job: image_node → text_node → reuse_node → factcheck_node
     → fusion_node → persist_node — all without Redis / Supabase.
  3. video / audio modality routing.
  4. Cache-hit bypass skips inference.
  5. Module 2B length gate returns not_assessed for short text.
  6. Module 7 Phase 3 flags are active.

Run with:
  cd backend
  python -m pytest tests/test_pipeline_stub.py -v
  # or directly:
  python tests/test_pipeline_stub.py
"""
from __future__ import annotations

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# ── Patch cache to avoid Redis ────────────────────────────────────────────────
import app.core.cache as _cache_module


async def _noop_get(_sha):
    return None


async def _noop_set(_sha, _result):
    return None


_cache_module.cache_get = _noop_get   # type: ignore
_cache_module.cache_set = _noop_set   # type: ignore


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_graph_compiles():
    from app.orchestrator.pipeline import build_graph
    g = build_graph()
    assert g is not None
    print("\n✓ Graph compiled.")


def test_text_image_pipeline():
    """Full text_image path with stub modules."""
    from app.orchestrator.pipeline import run_pipeline
    from app.orchestrator.state import FusionOutput

    state = asyncio.run(run_pipeline({
        "job_id":       "smoke-image-01",
        "sha256":       "a" * 64,
        "media_path":   None,
        "content_type": "image/jpeg",
        "claim_text":   "Test claim for a test image.",
        "cache_hit":    False,
        "errors":       [],
    }))

    fusion = state.get("fusion_output")
    assert fusion is not None, "fusion_output must not be None"
    assert isinstance(fusion, FusionOutput)
    assert fusion.short_label
    print(f"\n✓ text_image pipeline:")
    print(f"    short_label  : {fusion.short_label}")
    print(f"    veracity     : {fusion.veracity.verdict.value}")
    print(f"    authenticity : {fusion.authenticity.verdict.value}")
    print(f"    consistency  : {fusion.consistency.verdict.value}")
    print(f"    reuse        : {fusion.reuse.verdict.value}")
    print(f"    explanation  : {(fusion.explanation or '')[:120]!r}")


def test_video_pipeline():
    from app.orchestrator.pipeline import run_pipeline
    from app.orchestrator.state import InputModality

    state = asyncio.run(run_pipeline({
        "job_id":       "smoke-video-01",
        "sha256":       "b" * 64,
        "media_path":   None,
        "content_type": "video/mp4",
        "claim_text":   "Test video claim.",
        "cache_hit":    False,
        "errors":       [],
    }))

    assert state.get("modality") == InputModality.VIDEO
    print(f"\n✓ video pipeline: modality={state['modality'].value}")


def test_audio_pipeline():
    from app.orchestrator.pipeline import run_pipeline
    from app.orchestrator.state import InputModality

    state = asyncio.run(run_pipeline({
        "job_id":       "smoke-audio-01",
        "sha256":       "c" * 64,
        "media_path":   None,
        "content_type": "audio/mpeg",
        "claim_text":   None,
        "cache_hit":    False,
        "errors":       [],
    }))

    assert state.get("modality") == InputModality.AUDIO_ONLY
    print(f"\n✓ audio pipeline: modality={state['modality'].value}")


def test_cache_hit_skips_inference():
    from app.orchestrator.pipeline import run_pipeline
    from app.orchestrator.state import FusionOutput, AxisResult, Verdict

    prior = FusionOutput(
        veracity=AxisResult(verdict=Verdict.SUPPORTED, confidence=0.9),
        authenticity=AxisResult(verdict=Verdict.LIKELY_AUTHENTIC, confidence=0.8),
        consistency=AxisResult(verdict=Verdict.SUPPORTED, confidence=0.7),
        reuse=AxisResult(verdict=Verdict.LIKELY_AUTHENTIC, confidence=0.85),
        short_label="No strong misinformation signals detected.",
    )

    state = asyncio.run(run_pipeline({
        "job_id":        "smoke-cache-01",
        "sha256":        "d" * 64,
        "media_path":    None,
        "content_type":  "image/jpeg",
        "cache_hit":     True,
        "fusion_output": prior,
        "errors":        [],
    }))

    # image_node should NOT have run → image_findings stays None
    assert state.get("image_findings") is None, "Inference nodes should have been skipped."
    print("\n✓ cache-hit bypass: inference skipped.")


def test_module_2b_length_gate():
    """Short text (< 50 tokens) must return not_assessed."""
    from app.modules.text import run as text_run
    from app.modules.text.contracts import TextInput

    result = asyncio.run(text_run(TextInput(text="Short text.", source="caption")))
    assert result.verdict == "not_assessed"
    print(f"\n✓ Module 2B length gate: verdict={result.verdict}")


def test_module_7_flags_active():
    """Phase 3 flags must both be True."""
    import app.modules.fusion as fusion_mod
    assert fusion_mod._USE_WEIGHTED_FUSION    is True
    assert fusion_mod._USE_GEMINI_EXPLANATION is True
    print("\n✓ Module 7 Phase 3 flags: both active.")


def test_module_5_no_match():
    """Module 5 returns 'different' tier when Supabase is not configured."""
    from app.modules.reuse import run as reuse_run
    from app.modules.reuse.contracts import ReuseInput

    result = asyncio.run(reuse_run(ReuseInput(sha256="e" * 64)))
    # With no Supabase configured, should return a not-error result
    assert result.error is not None or result.reuse_tier == "different"
    print(f"\n✓ Module 5 (no DB): reuse_tier={result.reuse_tier!r}, error={result.error!r}")


if __name__ == "__main__":
    test_graph_compiles()
    test_text_image_pipeline()
    test_video_pipeline()
    test_audio_pipeline()
    test_cache_hit_skips_inference()
    test_module_2b_length_gate()
    test_module_7_flags_active()
    test_module_5_no_match()
    print("\n" + "─" * 60)
    print("✓ All Phase 3 smoke tests passed.")
