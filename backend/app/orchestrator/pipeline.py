"""
orchestrator/pipeline.py — LangGraph StateGraph wiring (Phase 3).

This is the ONLY file that imports LangGraph.  (architecture.md §6)

Graph shape (Phase 3):
  START
    └─► cache_check_node   (SHA-256 hit → skip inference)
          ├── [hit]   → persist_node → END
          └── [miss]  → router_node  (sets modality)
                          ├── image_node   (Module 2, Person 3)
                          ├── video_node   (Module 3, Person 2)
                          └── audio_node   (Module 4, Person 3)
                                └─► text_node      (Module 2B, Person 1)
                                      └─► reuse_node    (Module 5, Person 1)
                                            └─► factcheck_node (Module 6, Person 1A)
                                                  └─► fusion_node  (Module 7, Person 1)
                                                        └─► persist_node → END

Build-sequence notes (architecture.md §6):
  - Modality nodes (image/video/audio) are stubs until Person 2/3 deliver.
  - text_node (Module 2B) and reuse_node (Module 5) are REAL — Person 1 owns them.
  - factcheck_node is a stub until Person 1A delivers.
  - fusion_node is REAL — Phase 3 flags now active.
  - Per-claim Send fan-out lives INSIDE Module 6 (Person 1A), NOT here.
"""
from __future__ import annotations

import logging
from typing import Literal

from langgraph.graph import StateGraph, END

from app.orchestrator.state import GraphState, InputModality
from app.orchestrator.router_node import router_node, route_by_modality

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# Node implementations
# Each node does ONE thing: call the module's run() and return state updates.
# No logic is duplicated into nodes. (architecture.md §6)
# ══════════════════════════════════════════════════════════════════════════════


# ── Cache-check node ──────────────────────────────────────────────────────────

async def cache_check_node(state: GraphState) -> dict:
    """
    SHA-256 cache check.  On a hit, sets cache_hit=True and places the
    previously-computed fusion_output back into state so persist_node can
    update the Supabase job row to 'done' immediately.

    Also respects a pre-existing cache_hit=True in state (set by the
    worker or test harness when the result is already known).
    """
    # ── Pre-set cache hit (from worker or test) ───────────────────────────────
    if state.get("cache_hit"):
        return {}   # nothing to change — already marked as hit

    from app.core.cache import cache_get

    sha = state.get("sha256", "")
    if sha:
        cached = await cache_get(sha)
        if cached:
            logger.info("cache_check_node: HIT sha=%s…", sha[:12])
            return {
                "cache_hit":     True,
                "fusion_output": cached.get("fusion_output"),
            }
    return {"cache_hit": False}


def should_skip_inference(state: GraphState) -> Literal["router_node", "persist_node"]:
    """Conditional edge: cache hit → skip all inference."""
    return "persist_node" if state.get("cache_hit") else "router_node"


# ── Module 2 — Image node ─────────────────────────────────────────────────────

async def image_node(state: GraphState) -> dict:
    """
    Calls Module 2's run() (Person 3).
    Gracefully stubs when the real module is not yet implemented.
    """
    try:
        from app.modules.image import run as image_run
        from app.modules.image.contracts import ImageInput

        findings = await image_run(ImageInput(
            image_path=state.get("media_path"),
            claim_text=state.get("claim_text"),
        ))
        return {"image_findings": findings}

    except Exception as exc:    # noqa: BLE001
        from app.orchestrator.state import ImageFindings
        logger.exception("image_node: %s", exc)
        return {
            "image_findings": ImageFindings(error=str(exc)),
            "errors": [f"image_node: {exc}"],
        }


# ── Module 3 — Video node ─────────────────────────────────────────────────────

async def video_node(state: GraphState) -> dict:
    """Calls Module 3's run() (Person 2)."""
    try:
        from app.modules.video import run as video_run
        from app.modules.video.contracts import VideoInput

        findings = await video_run(VideoInput(
            video_path=state.get("media_path"),
            claim_text=state.get("claim_text"),
        ))
        return {"video_findings": findings}

    except Exception as exc:    # noqa: BLE001
        from app.orchestrator.state import VideoFindings
        logger.exception("video_node: %s", exc)
        return {
            "video_findings": VideoFindings(error=str(exc)),
            "errors": [f"video_node: {exc}"],
        }


# ── Module 4 — Audio node ─────────────────────────────────────────────────────

async def audio_node(state: GraphState) -> dict:
    """Calls Module 4's run() (Person 3)."""
    try:
        from app.modules.audio import run as audio_run
        from app.modules.audio.contracts import AudioInput

        findings = await audio_run(AudioInput(audio_path=state.get("media_path")))
        return {"audio_findings": findings}

    except Exception as exc:    # noqa: BLE001
        from app.orchestrator.state import AudioFindings
        logger.exception("audio_node: %s", exc)
        return {
            "audio_findings": AudioFindings(error=str(exc)),
            "errors": [f"audio_node: {exc}"],
        }


# ── Module 2B — Synthetic Text node (Person 1 — REAL) ────────────────────────

async def text_node(state: GraphState) -> dict:
    """
    Calls Module 2B on whatever text is available in state after the
    modality node has run.

    Priority for text source (architecture.md §Module 2B):
      1. Audio transcript (from audio_findings, best for video/audio paths)
      2. OCR text from image_findings
      3. User-supplied claim_text (caption)

    Returns synthetic_text_findings.
    """
    from app.modules.text import run as text_run
    from app.modules.text.contracts import TextInput

    # ── Determine text source ─────────────────────────────────────────────────
    audio_f = state.get("audio_findings")
    image_f = state.get("image_findings")

    text: str | None = None
    source: str | None = None

    if audio_f and audio_f.transcript:
        text   = audio_f.transcript
        source = "transcript"
    elif image_f and image_f.ocr_text:
        text   = image_f.ocr_text
        source = "ocr"
    elif state.get("claim_text"):
        text   = state["claim_text"]
        source = "caption"

    if not text or not source:
        # Nothing to score — leave synthetic_text_findings as None
        return {}

    try:
        findings = await text_run(TextInput(text=text, source=source))  # type: ignore[arg-type]
        return {"synthetic_text_findings": findings}

    except Exception as exc:    # noqa: BLE001
        logger.exception("text_node: %s", exc)
        from app.orchestrator.state import SyntheticTextFindings
        return {
            "synthetic_text_findings": SyntheticTextFindings(
                verdict="not_assessed",
                source=source,
                error=str(exc),
            ),
            "errors": [f"text_node: {exc}"],
        }


# ── Module 5 — Historical Reuse node (Person 1 — REAL) ───────────────────────

async def reuse_node(state: GraphState) -> dict:
    """Calls Module 5's run() — SHA-256 + pHash lookup against reference_media."""
    from app.modules.reuse import run as reuse_run
    from app.modules.reuse.contracts import ReuseInput

    try:
        findings = await reuse_run(ReuseInput(
            media_path=state.get("media_path"),
            sha256=state.get("sha256"),
        ))
        return {"reuse_findings": findings}

    except Exception as exc:    # noqa: BLE001
        from app.orchestrator.state import ReuseFindings
        logger.exception("reuse_node: %s", exc)
        return {
            "reuse_findings": ReuseFindings(error=str(exc)),
            "errors": [f"reuse_node: {exc}"],
        }


# ── Module 6 — Fact-Checking node (Person 1A — stub until delivered) ─────────

async def factcheck_node(state: GraphState) -> dict:
    """
    Calls Module 6's run() (Person 1A).

    SCOPE NOTE: the per-claim Send fan-out is INSIDE Module 6's own graph.
    This node calls run() as a black box.

    Claim source priority:
      1. Whisper transcript (audio_findings.transcript)
      2. User-supplied claim_text
    """
    claim = _resolve_claim(state)

    try:
        from app.modules.factcheck import run as factcheck_run
        from app.modules.factcheck.contracts import FactCheckInput

        findings = await factcheck_run(FactCheckInput(
            claim_text=claim,
            image_findings=state.get("image_findings"),
            reuse_findings=state.get("reuse_findings"),
        ))
        return {"claim_findings": findings}

    except Exception as exc:    # noqa: BLE001
        from app.orchestrator.state import ClaimFindings, Verdict
        logger.exception("factcheck_node: %s", exc)
        return {
            "claim_findings": ClaimFindings(
                overall_verdict=Verdict.NOT_ASSESSED,
                error=str(exc),
            ),
            "errors": [f"factcheck_node: {exc}"],
        }


def _resolve_claim(state: GraphState) -> str | None:
    audio = state.get("audio_findings")
    if audio and audio.transcript:
        return audio.transcript
    return state.get("claim_text")


# ── Module 7 — Fusion node (Person 1 — REAL, Phase 3 active) ─────────────────

async def fusion_node(state: GraphState) -> dict:
    """
    Calls Module 7's run().  This is the ONLY node allowed to read multiple
    module output fields.  (architecture.md §6 step 4)
    """
    from app.modules.fusion import run as fusion_run
    from app.modules.fusion.contracts import FusionInput

    inp = FusionInput(
        claim_text=state.get("claim_text"),
        image_findings=state.get("image_findings"),
        video_findings=state.get("video_findings"),
        audio_findings=state.get("audio_findings"),
        reuse_findings=state.get("reuse_findings"),
        synthetic_text_findings=state.get("synthetic_text_findings"),
        claim_findings=state.get("claim_findings"),
    )

    try:
        output = await fusion_run(inp)
        return {"fusion_output": output}
    except Exception as exc:    # noqa: BLE001
        from app.orchestrator.state import FusionOutput
        logger.exception("fusion_node: %s", exc)
        return {
            "fusion_output": FusionOutput(error=str(exc)),
            "errors": [f"fusion_node: {exc}"],
        }


# ── Persist node ──────────────────────────────────────────────────────────────

async def persist_node(state: GraphState) -> dict:
    """
    Write the final fusion_output to Supabase + Redis SHA-256 cache.
    Failures are logged but never re-raised — the result is already computed.
    """
    job_id        = state.get("job_id", "")
    sha           = state.get("sha256", "")
    fusion_output = state.get("fusion_output")

    if fusion_output is None:
        return {}

    result_dict = (
        fusion_output.model_dump()
        if hasattr(fusion_output, "model_dump") else {}
    )

    # ── Redis cache ───────────────────────────────────────────────────────────
    if sha:
        try:
            from app.core.cache import cache_set
            await cache_set(sha, {"job_id": job_id, "fusion_output": result_dict})
        except Exception as exc:    # noqa: BLE001
            logger.warning("persist_node Redis write failed: %s", exc)

    # ── Supabase ──────────────────────────────────────────────────────────────
    if job_id:
        try:
            from app.core.supabase_client import get_supabase
            sb = get_supabase()
            sb.table("jobs").update({
                "status":      "done",
                "result_json": result_dict,
            }).eq("id", job_id).execute()
        except Exception as exc:    # noqa: BLE001
            logger.warning("persist_node Supabase write failed: %s", exc)

    return {}


# ══════════════════════════════════════════════════════════════════════════════
# Graph assembly
# ══════════════════════════════════════════════════════════════════════════════

def build_graph() -> StateGraph:
    """
    Assemble and compile the LangGraph StateGraph.
    Called once at startup; the compiled graph is stateless and concurrency-safe.
    """
    builder = StateGraph(GraphState)

    # ── Nodes ─────────────────────────────────────────────────────────────────
    builder.add_node("cache_check_node", cache_check_node)
    builder.add_node("router_node",      router_node)
    builder.add_node("image_node",       image_node)
    builder.add_node("video_node",       video_node)
    builder.add_node("audio_node",       audio_node)
    builder.add_node("text_node",        text_node)       # Module 2B — NEW
    builder.add_node("reuse_node",       reuse_node)
    builder.add_node("factcheck_node",   factcheck_node)
    builder.add_node("fusion_node",      fusion_node)
    builder.add_node("persist_node",     persist_node)

    # ── Entry point ───────────────────────────────────────────────────────────
    builder.set_entry_point("cache_check_node")

    # ── Edges ─────────────────────────────────────────────────────────────────

    # cache hit → skip everything
    builder.add_conditional_edges(
        "cache_check_node",
        should_skip_inference,
        {"router_node": "router_node", "persist_node": "persist_node"},
    )

    # router → modality branch
    builder.add_conditional_edges(
        "router_node",
        route_by_modality,
        {
            "image_node": "image_node",
            "video_node": "video_node",
            "audio_node": "audio_node",
        },
    )

    # all three modality branches converge at text_node (Module 2B)
    for src in ("image_node", "video_node", "audio_node"):
        builder.add_edge(src, "text_node")

    # linear tail: text → reuse → factcheck → fusion → persist → END
    builder.add_edge("text_node",      "reuse_node")
    builder.add_edge("reuse_node",     "factcheck_node")
    builder.add_edge("factcheck_node", "fusion_node")
    builder.add_edge("fusion_node",    "persist_node")
    builder.add_edge("persist_node",   END)

    return builder.compile()


# ── Singleton ─────────────────────────────────────────────────────────────────

_graph = None


def get_graph():
    """Return the compiled graph (lazy singleton)."""
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


async def run_pipeline(initial_state: dict) -> GraphState:
    """
    Run the full pipeline for one job.
    Called from the ARQ worker.  Returns the final GraphState.
    """
    graph = get_graph()
    return await graph.ainvoke(initial_state)
