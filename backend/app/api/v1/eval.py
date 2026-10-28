"""
api/v1/eval.py — GET /api/v1/eval/{module}

Returns Module 8's latest eval report for a given module.
Used by the demo analytics dashboard to surface per-module
accuracy / F1 / FPR / latency metrics.

Each person owns their module's eval slice:
  - Person 1:  modules ["reuse", "text", "fusion"]
  - Person 1A: modules ["factcheck"]
  - Person 2:  modules ["video"]
  - Person 3:  modules ["image", "audio"]

Reports are stored in Supabase (eval_reports table) and/or
as JSON files at data/eval_sets/<module>/eval_report.json.
"""
from __future__ import annotations

import json
import os
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

# Valid module names (must match architecture.md module list)
VALID_MODULES = frozenset({
    "image", "text", "video", "audio",
    "reuse", "factcheck", "fusion", "overall",
})

# Path to local eval report files (relative to the project root)
_EVAL_DIR = os.path.join(
    os.path.dirname(__file__),          # .../api/v1/
    "..", "..", "..", "..",             # up to project root
    "data", "eval_sets",
)


# ── Response model ────────────────────────────────────────────────────────────

class EvalReport(BaseModel):
    module:         str
    timestamp:      Optional[str]              = None
    accuracy:       Optional[float]            = None
    f1_score:       Optional[float]            = None
    false_positive_rate: Optional[float]       = None
    latency_ms_p95: Optional[float]            = None
    sample_count:   Optional[int]              = None
    notes:          Optional[str]              = None
    raw:            Optional[dict[str, Any]]   = None  # full report for advanced views


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_local_report(module: str) -> dict | None:
    """Try to load a local eval_report.json for the module."""
    path = os.path.normpath(
        os.path.join(_EVAL_DIR, module, "eval_report.json")
    )
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    return None


async def _load_supabase_report(module: str) -> dict | None:
    """Try to load the latest eval report row from Supabase."""
    try:
        from app.core.supabase_client import get_supabase
        sb = get_supabase()
        resp = (
            sb.table("eval_reports")
              .select("*")
              .eq("module", module)
              .order("created_at", desc=True)
              .limit(1)
              .execute()
        )
        if resp.data:
            return resp.data[0]
    except Exception:
        pass
    return None


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.get("/eval/{module}", response_model=EvalReport)
async def get_eval_report(module: str):
    """
    Return the latest eval report for *module*.

    Reports are surfaced in the frontend analytics view for demo/judging
    credibility.  (architecture.md Module 9, step 5)

    Priority: Supabase eval_reports table → local data/eval_sets/<module>/eval_report.json.
    Returns 404 if no report has been generated yet.
    """
    module = module.lower()
    if module not in VALID_MODULES:
        raise HTTPException(
            422,
            f"Unknown module {module!r}. Valid values: {sorted(VALID_MODULES)}",
        )

    # ── Try Supabase ──────────────────────────────────────────────────────────
    row = await _load_supabase_report(module)
    if row:
        return EvalReport(
            module          = module,
            timestamp       = row.get("created_at"),
            accuracy        = row.get("accuracy"),
            f1_score        = row.get("f1_score"),
            false_positive_rate = row.get("false_positive_rate"),
            latency_ms_p95  = row.get("latency_ms_p95"),
            sample_count    = row.get("sample_count"),
            notes           = row.get("notes"),
            raw             = row,
        )

    # ── Try local file ────────────────────────────────────────────────────────
    local = _load_local_report(module)
    if local:
        return EvalReport(
            module          = module,
            timestamp       = local.get("timestamp"),
            accuracy        = local.get("accuracy"),
            f1_score        = local.get("f1_score"),
            false_positive_rate = local.get("false_positive_rate"),
            latency_ms_p95  = local.get("latency_ms_p95"),
            sample_count    = local.get("sample_count"),
            notes           = local.get("notes"),
            raw             = local,
        )

    raise HTTPException(
        404,
        f"No eval report found for module {module!r}. "
        "Run the Module 8 eval harness to generate one.",
    )
