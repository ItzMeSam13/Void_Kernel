"""
worker.py — ARQ worker entrypoint (Module 1, Phase 2).

This is the ONLY place that ties together:
  - ARQ (job queue)
  - The compiled LangGraph pipeline (orchestrator/pipeline.py)
  - Media temp-file management

Architecture rule (architecture.md §6):
  The worker imports from orchestrator/ — never from individual module
  internals directly.

Usage:
  arq app.worker.WorkerSettings
"""
from __future__ import annotations

import logging
import os
import tempfile
import uuid
from typing import Any

from app.core.cache import arq_redis_settings

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# Task functions (called by ARQ workers)
# ══════════════════════════════════════════════════════════════════════════════

async def analyze_task(
    ctx: dict,
    *,
    job_id: str,
    sha256: str,
    raw_bytes: bytes,
    filename: str,
    content_type: str,
    claim_text: str | None,
) -> dict[str, Any]:
    """
    ARQ task: run the full LangGraph pipeline for one uploaded media file.

    Steps:
      1. Write raw_bytes to a temp file so module run()s can open it by path.
      2. Build the initial GraphState.
      3. Run the compiled pipeline (cache-check → router → modules → fusion).
      4. Return the fusion_output dict (ARQ stores this as the job result).
    """
    from app.orchestrator.pipeline import run_pipeline

    # ── Write temp file ───────────────────────────────────────────────────────
    suffix = _ext_from_content_type(content_type)
    tmp_path: str | None = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(raw_bytes)
            tmp_path = tmp.name

        logger.info(
            "analyze_task job=%s sha=%s content_type=%s size=%dB tmp=%s",
            job_id, sha256[:12], content_type, len(raw_bytes), tmp_path,
        )

        # ── Build initial state ───────────────────────────────────────────────
        initial_state: dict = {
            "job_id":       job_id,
            "sha256":       sha256,
            "media_path":   tmp_path,
            "content_type": content_type,
            "claim_text":   claim_text,
            "cache_hit":    False,
            "errors":       [],
            "_raw_bytes":   None,   # don't carry raw bytes through the graph
        }

        # ── Run pipeline ──────────────────────────────────────────────────────
        final_state = await run_pipeline(initial_state)

        fusion_output = final_state.get("fusion_output")
        result = fusion_output.model_dump() if hasattr(fusion_output, "model_dump") else {}

        return {
            "job_id":        job_id,
            "sha256":        sha256,
            "fusion_output": result,
            "errors":        final_state.get("errors", []),
        }

    except Exception as exc:  # noqa: BLE001
        logger.exception("analyze_task job=%s FAILED: %s", job_id, exc)
        # Mark the Supabase job row as failed
        _mark_failed(job_id, str(exc))
        return {"job_id": job_id, "error": str(exc)}

    finally:
        # Always clean up the temp file
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def _ext_from_content_type(ct: str) -> str:
    """Map MIME type to a file extension for the temp file."""
    _map = {
        "image/jpeg": ".jpg",
        "image/png":  ".png",
        "image/webp": ".webp",
        "image/gif":  ".gif",
        "video/mp4":  ".mp4",
        "video/quicktime": ".mov",
        "video/webm": ".webm",
        "video/x-matroska": ".mkv",
        "audio/mpeg": ".mp3",
        "audio/wav":  ".wav",
        "audio/ogg":  ".ogg",
        "audio/flac": ".flac",
    }
    return _map.get(ct.lower().split(";")[0].strip(), ".bin")


def _mark_failed(job_id: str, error: str) -> None:
    """Update the Supabase jobs row to status='failed'. Best-effort."""
    try:
        from app.core.supabase_client import get_supabase
        sb = get_supabase()
        sb.table("jobs").update({
            "status": "failed",
            "error":  error[:1000],
        }).eq("id", job_id).execute()
    except Exception:  # noqa: BLE001
        pass


# ══════════════════════════════════════════════════════════════════════════════
# Public enqueue helper — called from api/v1/analyze.py
# ══════════════════════════════════════════════════════════════════════════════

async def enqueue_analysis(
    *,
    job_id: str,
    sha256: str,
    raw_bytes: bytes,
    filename: str,
    content_type: str,
    claim_text: str | None,
) -> None:
    """
    Push an analyze_task onto the ARQ queue.
    Called by the FastAPI upload endpoint (api/v1/analyze.py).
    """
    import arq

    pool = await arq.create_pool(arq_redis_settings())
    await pool.enqueue_job(
        "analyze_task",
        job_id=job_id,
        sha256=sha256,
        raw_bytes=raw_bytes,
        filename=filename,
        content_type=content_type,
        claim_text=claim_text,
    )
    await pool.close()


# ══════════════════════════════════════════════════════════════════════════════
# ARQ WorkerSettings — `arq app.worker.WorkerSettings` starts the worker
# ══════════════════════════════════════════════════════════════════════════════

class WorkerSettings:
    """
    ARQ worker configuration.
    Run with: `arq app.worker.WorkerSettings`
    """
    functions = [analyze_task]
    redis_settings = arq_redis_settings()
    max_jobs = 4             # concurrent jobs per worker process
    job_timeout = 300        # 5 minutes per job (video can be slow)
    keep_result = 3600 * 24  # keep job result in Redis for 24 h
