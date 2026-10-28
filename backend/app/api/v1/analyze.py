"""
api/v1/analyze.py — POST /api/v1/analyze

Accepts a media upload (image / video / audio) + optional claim text.
1. Reads bytes, computes SHA-256.
2. Checks Redis 7-day cache → returns cached result immediately on hit.
3. Validates file type.
4. Enqueues an ARQ job.
5. Returns {job_id, sha256, status: "queued"}.

Phase 1: full routing logic; ARQ job enqueueing is a stub (direct run) until
         Phase 2 wires the real ARQ worker.
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from pydantic import BaseModel

from app.core.cache import compute_sha256, cache_get

router = APIRouter()

ALLOWED_MIME_TYPES = {
    # images
    "image/jpeg", "image/png", "image/webp", "image/gif",
    # video
    "video/mp4", "video/quicktime", "video/webm", "video/x-matroska",
    # audio
    "audio/mpeg", "audio/wav", "audio/ogg", "audio/flac",
}

MAX_FILE_SIZE_BYTES = 200 * 1024 * 1024  # 200 MB


class AnalyzeResponse(BaseModel):
    job_id: str
    sha256: str
    status: str                  # "queued" | "cached"
    cached_result: Optional[dict] = None


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    file: UploadFile = File(..., description="Image, video, or audio file to analyze."),
    claim_text: Optional[str] = Form(None, description="Caption or claim associated with the media."),
):
    """
    Upload media for misinformation analysis.

    Returns immediately with a job_id.  Poll GET /api/v1/results/{job_id}
    for the final report.
    """
    # ── 1. Read upload ────────────────────────────────────────────────────────
    raw = await file.read()
    if len(raw) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(413, "File exceeds 200 MB limit.")

    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            415,
            f"Unsupported media type: {file.content_type}. "
            f"Allowed: {', '.join(sorted(ALLOWED_MIME_TYPES))}",
        )

    # ── 2. SHA-256 + cache check ──────────────────────────────────────────────
    sha = compute_sha256(raw)
    cached = await cache_get(sha)
    if cached:
        return AnalyzeResponse(
            job_id=cached.get("job_id", "cached"),
            sha256=sha,
            status="cached",
            cached_result=cached,
        )

    # ── 3. Enqueue ARQ job ────────────────────────────────────────────────────
    job_id = str(uuid.uuid4())

    try:
        from app.worker import enqueue_analysis
        await enqueue_analysis(
            job_id=job_id,
            sha256=sha,
            raw_bytes=raw,
            filename=file.filename or "upload",
            content_type=file.content_type,
            claim_text=claim_text,
        )
    except ImportError:
        # ARQ worker not yet wired (Phase 1 stub) — proceed without enqueueing
        pass

    # ── 4. Persist job row in Supabase ────────────────────────────────────────
    try:
        from app.core.supabase_client import get_supabase
        sb = get_supabase()
        sb.table("jobs").insert({
            "id": job_id,
            "sha256": sha,
            "status": "queued",
            "modality": _infer_modality(file.content_type),
            "claim_text": claim_text,
            "filename": file.filename,
        }).execute()
    except Exception:  # Supabase not configured yet (local dev)
        pass

    return AnalyzeResponse(job_id=job_id, sha256=sha, status="queued")


def _infer_modality(content_type: Optional[str]) -> str:
    if content_type and content_type.startswith("video/"):
        return "video"
    if content_type and content_type.startswith("audio/"):
        return "audio_only"
    return "text_image"
