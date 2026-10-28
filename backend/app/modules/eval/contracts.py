"""
modules/eval/contracts.py — Module 8 public contracts.

EvalInput / EvalReport form the interface for the evaluation harness.
Each person owns their module's eval slice.
"""
from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


class EvalInput(BaseModel):
    """Input to Module 8's run_eval() entrypoint."""
    module:        str             = Field(..., description="Module name to evaluate.")
    test_set_path: Optional[str]  = Field(None, description="Path to labeled test set directory.")
    augment:       bool            = Field(False,
        description="Run adversarial augmentation pass (recompress, rescale, re-encode).")


class EvalReport(BaseModel):
    """
    Per-module evaluation report.
    Written to data/eval_sets/<module>/eval_report.json
    and to Supabase eval_reports table.
    """
    module:               str
    timestamp:            Optional[str]           = None
    accuracy:             Optional[float]         = Field(None, ge=0.0, le=1.0)
    f1_score:             Optional[float]         = Field(None, ge=0.0, le=1.0)
    false_positive_rate:  Optional[float]         = Field(None, ge=0.0, le=1.0)
    latency_ms_p95:       Optional[float]         = None
    sample_count:         Optional[int]           = None
    augmentation_results: Optional[dict[str, Any]] = Field(None,
        description="Verdict-diff summary after adversarial augmentation pass.")
    notes:                Optional[str]           = None
    error:                Optional[str]           = None
