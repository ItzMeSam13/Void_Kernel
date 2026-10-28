"""
api/v1/results.py — GET /api/v1/results/{job_id}
                    GET /api/v1/results/{job_id}/report

Polls job status and returns the full structured result or
the rendered explanation + evidence report.

Phase 1: reads from Supabase `jobs` table; falls back to Redis
         ARQ job store if Supabase is not configured.
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


# ── Response models ───────────────────────────────────────────────────────────

class JobStatusResponse(BaseModel):
    job_id:        str
    status:        str             # queued | processing | done | failed
    sha256:        Optional[str]   = None
    modality:      Optional[str]   = None
    fusion_output: Optional[dict]  = None  # None until status == "done"
    errors:        list[str]       = []
    error:         Optional[str]   = None  # top-level error if status == "failed"


class ReportResponse(BaseModel):
    """Rendered explanation + per-axis evidence for the frontend result card."""
    job_id:        str
    explanation:   Optional[str]  = None
    short_label:   Optional[str]  = None
    axes: dict[str, Any]          = {}    # veracity / authenticity / consistency / reuse
    claim_text:    Optional[str]  = None


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _fetch_job(job_id: str) -> dict | None:
    """
    Try Supabase first, then Redis ARQ job store.
    Returns the raw job row dict, or None if not found.
    """
    # ── Supabase ──────────────────────────────────────────────────────────────
    try:
        from app.core.supabase_client import get_supabase
        sb = get_supabase()
        resp = sb.table("jobs").select("*").eq("id", job_id).single().execute()
        if resp.data:
            return resp.data
    except Exception:
        pass

    # ── Redis ARQ job store ───────────────────────────────────────────────────
    try:
        import arq
        from app.core.cache import arq_redis_settings
        pool = await arq.create_pool(arq_redis_settings())
        job  = await pool.job(job_id)   # returns None if not found
        await pool.close()
        if job:
            return {
                "id":          job_id,
                "status":      "done" if await job.status() == arq.JobStatus.complete else "queued",
                "result_json": await job.result() if await job.status() == arq.JobStatus.complete else None,
            }
    except Exception:
        pass

    return None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/results/{job_id}", response_model=JobStatusResponse)
async def get_results(job_id: str):
    """
    Poll job status and retrieve the full structured result.

    Returns 404 if the job_id is unknown.
    Returns the fusion_output dict once status == "done".
    """
    row = await _fetch_job(job_id)
    if row is None:
        raise HTTPException(404, f"Job {job_id!r} not found.")

    status    = row.get("status", "unknown")
    result    = row.get("result_json") or {}
    fusion    = result.get("fusion_output") if result else None
    errors    = result.get("errors", []) if result else []
    top_error = row.get("error")

    return JobStatusResponse(
        job_id        = job_id,
        status        = status,
        sha256        = row.get("sha256"),
        modality      = row.get("modality"),
        fusion_output = fusion,
        errors        = errors,
        error         = top_error,
    )


@router.get("/results/{job_id}/report", response_model=ReportResponse)
async def get_report(job_id: str):
    """
    Return the rendered explanation + per-axis evidence for the frontend
    result view (axis cards + confidence breakdown + explanation paragraph).
    """
    row = await _fetch_job(job_id)
    if row is None:
        raise HTTPException(404, f"Job {job_id!r} not found.")

    status = row.get("status", "unknown")
    if status not in ("done",):
        raise HTTPException(
            202,
            {"detail": f"Job {job_id!r} is not yet complete (status={status!r})."},
        )

    result_json  = row.get("result_json") or {}
    fusion_dict  = result_json.get("fusion_output", {})
    claim_text   = row.get("claim_text")

    # Extract per-axis dicts for the frontend card layout
    axes = {
        "veracity":     fusion_dict.get("veracity",     {}),
        "authenticity": fusion_dict.get("authenticity", {}),
        "consistency":  fusion_dict.get("consistency",  {}),
        "reuse":        fusion_dict.get("reuse",        {}),
    }

    return ReportResponse(
        job_id      = job_id,
        explanation = fusion_dict.get("explanation"),
        short_label = fusion_dict.get("short_label"),
        axes        = axes,
        claim_text  = claim_text,
    )
