"""
modules/eval/__init__.py — Module 8 eval harness entrypoint (stub).

Each person implements their slice:
  - Person 1:  reuse, text, fusion eval slices
  - Person 1A: factcheck eval slice
  - Person 2:  video eval slice
  - Person 3:  image, audio eval slices
"""
from __future__ import annotations

from app.modules.eval.contracts import EvalInput, EvalReport


async def run_eval(inp: EvalInput) -> EvalReport:
    """
    STUB — each person fills in their module's eval slice.

    Full implementation (architecture.md §Module 8):
      1. Load labeled test set from inp.test_set_path.
      2. Run the module's run() on each sample.
      3. Compute accuracy / F1 / FPR / latency (p95).
      4. If inp.augment: recompress/rescale test media, re-run, diff verdicts.
      5. Write eval_report.json to data/eval_sets/<module>/.
      6. Upsert row in Supabase eval_reports table.
    """
    return EvalReport(
        module=inp.module,
        error=f"Module 8 eval harness not yet implemented for module={inp.module!r} — stub.",
    )
